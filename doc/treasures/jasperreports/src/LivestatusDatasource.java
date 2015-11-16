package livestatus;

import java.util.ArrayList;
import java.util.HashMap;

import net.sf.jasperreports.engine.*;

public class LivestatusDatasource implements JRDataSource, JRRewindableDataSource {
	private int                           m_nIdx; // line index
	private ArrayList<ArrayList<String>>  data;   // actual data
	private ArrayList<String>             headers = new ArrayList<String>(); // header information
	private HashMap<String, String> 	  map_fieldtypes;
	private HashMap<String, String>       map_fielddescr;
	
	public LivestatusDatasource(ArrayList<ArrayList<String>> array, 
								HashMap<String,String> fieldtypes, HashMap<String, String> fielddescr) {
		m_nIdx = 0; 
		data = array;
		map_fieldtypes = fieldtypes;
		map_fielddescr = fielddescr;
		for( String fieldname: array.get(0) )
			headers.add(fieldname.toString());
	}

	protected String[] getHeaders(){
		String[] result = new String[headers.size()];
		return headers.toArray(result);		
	}

	protected String getFieldDescription(String fieldname){
		try{ 
			if (map_fielddescr.containsKey(fieldname))
				return map_fielddescr.get(fieldname);
			else
				return "";
		}catch(Exception ex){
			return "";
		}
	}
	
	protected String getFieldType(String fieldname){
		try{ 
			if (map_fieldtypes.containsKey(fieldname))
				return map_fieldtypes.get(fieldname);
			else
				return "";			
		}catch(Exception ex){
			return "";
		}
	}
	
	protected ArrayList<ArrayList<String>> getData(){
		return data;
	}


	public Object getFieldValue(JRField field) throws JRException {
		String fieldname = field.getName();
		int column = headers.indexOf(fieldname);
		if( column < 0 || column >= data.get(0).size() ) {
			throw new JRException("Unknown Field:" + fieldname);
		}
		
		String value = (data.get(m_nIdx)).get(column);
		// Cast string value according to type
		if( map_fieldtypes.containsKey(fieldname) ){
			String fieldtype = map_fieldtypes.get(fieldname);
			if(fieldtype.equals("int")){
				return Integer.parseInt(value);
			}else if(fieldtype.equals("float")){
				return Float.parseFloat(value);			
			}else if(fieldtype.equals("list")){
				ArrayList<String> res_list = new ArrayList<String>();
				String[] tokens = value.split("\\|");
				for( int i = 0; i<tokens.length; i++){
					res_list.add(tokens[i]);
				}
				return res_list;
			}
		}
		// If no fieldtype is available, return the value as string
		return value;
	}

	
	public boolean next() throws JRException {
		m_nIdx++;
		return (m_nIdx < data.size());
	}

	public void moveFirst() throws JRException {
		m_nIdx = 0;
	}
}