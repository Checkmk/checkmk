package livestatus;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.net.SocketAddress;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;

import net.sf.jasperreports.engine.JRDataset;
import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.query.JRQueryExecuter;

public class LivestatusQueryExecuter implements JRQueryExecuter{
	// Connection parameters
	private String    			jasper_query;     // Query from jasperreports incl. connection details
	private String    			livestatus_query; // Query send to livestatus
	private String    			server;           // server name
	private int       			server_port;      // server port
	private int 				timeoutInMs = 10*1000;  // 10 seconds
	private String    			fixed_appendix = "\nColumnHeaders: on\nResponseHeader: fixed16\nOutputFormat: csv\n\n";

	// Socket parameters
	private Socket    			socket;           // socket to server
	private OutputStream 		sockOutput;       // socket output stream
	private InputStream 		sockInput;        // socket input stream
	private BufferedReader 		in;               // InputStream reader

	
	public static void main(String[] args){
		try {
			//new LivestatusQueryExecuter("localhost 6561\nGET services\nColumns: host_name check_command").createDatasource();
		
			String query = "localhost 6561\nGET statehist\nColumns: state host_name service_description\nFilter: time >= 1344195720\nFilter: time <= 1344196820\nFilter: service_description = CPU load\nFilter: host_name = localhost\nStats: sum duration_ok\nStats: sum duration_warning\nStats: sum duration_critical";
			new LivestatusQueryExecuter(query).createDatasource();
			
		} catch (JRException e) {
			// TODO Auto-generated catch block
			e.printStackTrace();
		}		
	}
	
	public LivestatusQueryExecuter(String query) {
		this.jasper_query = query; 
	}

	@SuppressWarnings("rawtypes")
	public LivestatusQueryExecuter(JRDataset dataset, Map parameters) {
		this.jasper_query = dataset.getQuery().getText(); 
	}

	private void evaluateQuery() throws JRException{
		// check for blank lines
		for( String line : jasper_query.split("\n") ){
			if( line.trim().isEmpty() )
				throw new JRException("LQL Query: Remove blank lines from query");			
		}

		String target_info = jasper_query.split("\n")[0];
		livestatus_query   = jasper_query.substring(target_info.length()+1);
		server      = target_info.split(" ")[0];
		server_port = Integer.parseInt(target_info.split(" ")[1]);
	}

	public boolean cancelQuery() throws JRException {
		System.out.println("ABORT QUERY");
		try {
			if( socket.isConnected() ){
				System.out.println("STOPPED !");
				socket.close();
				return true;
			}
		}catch (IOException e) {
			throw new JRException(e.getMessage());
		}
		return false;
	}

	public void close() {
	}

	private void setupSocket() throws JRException{
		InetAddress   inteAddress;
		SocketAddress socketAddress;
		
		try {
			inteAddress = InetAddress.getByName(server);
			socketAddress = new InetSocketAddress(inteAddress, server_port);
			socket = new Socket();
			socket.connect(socketAddress, timeoutInMs);
			sockOutput = socket.getOutputStream();
			sockInput  = socket.getInputStream();
			in = new BufferedReader(new InputStreamReader(sockInput));
		} catch (Exception e) {
			throw new JRException("Unable to connect to " + server + " " + server_port + " " + e.getMessage());
		}
	}
	
	
	public LivestatusDatasource createDatasource() throws JRException {
		// conduct query syntax check and determine connection parameters
		evaluateQuery();
		
		// Parameters passed to the LivestatusDatasource
		ArrayList<ArrayList<String>> livestatus_data = new ArrayList<ArrayList<String>>();
		HashMap<String,String> map_fielddesc = new HashMap<String, String>(); // Column descriptions
		HashMap<String,String> map_fieldtype = new HashMap<String, String>(); // Column field classes
		
		try
		{
			// setup socket and in/output streams
			setupSocket();
			
			// query the column types and their descriptions
			String table_name = livestatus_query.split("\n")[0].split(" ")[1];
			String desc_query = String.format("GET columns\nFilter: table = %s\nColumnHeaders: off\nResponseHeader: fixed16\nOutputFormat: csv\nKeepAlive: on\n\n", table_name);
			sockOutput.write(desc_query.getBytes(), 0, desc_query.getBytes().length); 
			
			// read description information
			String[] responseHeader = in.readLine().split("\\s");
			int response_size = Integer.parseInt(responseHeader[responseHeader.length-1]);
			int offset = 0;
			String line;
			line = in.readLine(); // Skip column headers
			offset += line.getBytes().length + 1;
			while( offset < response_size ){
				line = in.readLine();
				if( line == null )
					break;
				offset += line.getBytes().length + 1;
				map_fielddesc.put(line.split(";")[1],line.split(";")[0]);
				map_fieldtype.put(line.split(";")[1],line.split(";")[3]);
			}

			// send livestatus query to socket
			sockOutput.write(livestatus_query.getBytes(), 0, livestatus_query.getBytes().length); 
			sockOutput.write(fixed_appendix.getBytes(), 0, fixed_appendix.getBytes().length); 
		
			// check if response is valid
			responseHeader = in.readLine().split("\\s");
			if( ! responseHeader[0].equals("200") ){
				String error = "";
				while(true){
					line = in.readLine();
					if( line == null )
						break;
					error.concat(line+"\n");
				}
				throw new JRException("Livestatus response: \n" + responseHeader + " \n" + error);
			}
			
			// check if response size not exceeding 10MB
			response_size = Integer.parseInt(responseHeader[responseHeader.length-1]);
			if( response_size > 10 * 1024 * 1024 )
				throw new JRException("Livestatus answer exceeds 10 MB. Aborting..");
		
			// read content
			offset = 0;
			offset += line.getBytes().length + 1;
			while( offset < response_size ){
				line = in.readLine();
				if( line == null )
					break;
				ArrayList<String> tmp_array = new ArrayList<String>();
				for( String field : line.split(";") ){
					tmp_array.add(field);
				}
				livestatus_data.add(tmp_array);
			}

			// close sockets
			sockInput.close();
			sockOutput.close();
			socket.close();
		}catch (JRException jre) {
			throw jre;
		}
		catch (Exception e) {
			e.printStackTrace();
			throw new JRException(String.format("Unable to process query: " + e.getMessage()));
		}
		
		// Create and return the LivestatusDatasource
		return new LivestatusDatasource(livestatus_data, map_fieldtype, map_fielddesc);
	}
}