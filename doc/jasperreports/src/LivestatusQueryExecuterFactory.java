package livestatus;

import java.util.Map;
import net.sf.jasperreports.engine.JRDataset;
import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.JRValueParameter;
import net.sf.jasperreports.engine.query.JRQueryExecuter;
import net.sf.jasperreports.engine.query.JRQueryExecuterFactory;

@SuppressWarnings("deprecation")
public class LivestatusQueryExecuterFactory implements JRQueryExecuterFactory{
	public JRQueryExecuter createQueryExecuter(JRDataset dataset, Map<String, 
			? extends JRValueParameter> parameters) throws JRException {
		// TODO Auto-generated method stub
		logFile("Create livestatusQueryExecut0r!\n");
		return new LivestatusQueryExecuter(dataset, parameters);
		
	}
static	public void logFile(String info){
//		FileWriter writer;
//		File file;
//
//		file = new File("/tmp/ireport.txt");
//		try {
//			writer = new FileWriter(file, true);
//			writer.write(info);
//			writer.write("\n");
//			writer.flush();
//			writer.close();
//		}catch (IOException e) {
//			e.printStackTrace();
//		}
	}


	public Object[] getBuiltinParameters() {
		return null;
	}

	public boolean supportsQueryParameterType(String arg0) {
		return false;
	}
}
