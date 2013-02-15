package livestatus;

import java.util.ArrayList;
import java.util.Map;
import java.util.Vector;

import net.sf.jasperreports.engine.JRDataset;
import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.JRField;
import net.sf.jasperreports.engine.design.JRDesignField;

import com.jaspersoft.ireport.designer.FieldsProvider;
import com.jaspersoft.ireport.designer.FieldsProviderEditor;
import com.jaspersoft.ireport.designer.IReportConnection;
import com.jaspersoft.ireport.designer.data.ReportQueryDialog;

public class LivestatusFieldsProvider implements FieldsProvider{

	public String designQuery(IReportConnection arg0, String arg1,
			ReportQueryDialog arg2) throws JRException,
			UnsupportedOperationException {
		return null;
	}

	public FieldsProviderEditor getEditorComponent(ReportQueryDialog arg0) {
		return null;
	}

	public boolean hasEditorComponent() {
		return false;
	}

	public boolean hasQueryDesigner() {
		return false;
	}

	public boolean supportsAutomaticQueryExecution() {
		return true;
	}

	public boolean supportsGetFieldsOperation() {
		return true;
	}

	@Override
	public JRField[] getFields(IReportConnection arg0, JRDataset dataset, Map parameters)
			throws JRException, UnsupportedOperationException {
		JRField[] ret = null;
		
		try{
			Vector<JRDesignField> jr_vector = new Vector<JRDesignField>();

			// Disable data columns. We only need the header line
			String query = dataset.getQuery().getText().concat("\nLimit: 0");
			LivestatusDatasource data = new LivestatusQueryExecuter(query, parameters).createDatasource();
			
			String[] headers = data.getHeaders();
			int header_count = headers.length;
			String descr;
			String type;
						
			
			for( int i = 0; i < header_count; i++ ){
				// Set field name
				JRDesignField tmp_field = new JRDesignField();
				tmp_field.setName(headers[i]);
				
				// Add field description, if available
				descr = data.getFieldDescription(headers[i]);
				if( ! descr.equals("") )
					tmp_field.setDescription(descr);

				// Add field class type
				type  = data.getFieldType(headers[i]);
				if( ! type.equals("") ){
					if(type.equals("int")){
						tmp_field.setValueClass(Integer.class);
						tmp_field.setValueClassName(Integer.class.getName());
					}
					else if(type.equals("float")){
						tmp_field.setValueClass(Float.class);
						tmp_field.setValueClassName(Float.class.getName());
					}else if(type.equals("list")){
						tmp_field.setValueClass(ArrayList.class);
						tmp_field.setValueClassName(ArrayList.class.getName());
					}
					else{ // String and everything else
						tmp_field.setValueClass(String.class);
						tmp_field.setValueClassName(String.class.getName());
					}						
				}else{
					tmp_field.setValueClass(String.class);
					tmp_field.setValueClassName(String.class.getName());
				}
				jr_vector.add(tmp_field);
			}
			ret = new JRField[jr_vector.size()];
			jr_vector.toArray(ret);
		}catch(JRException jrex){
			throw new JRException("Jasper Error evaluating query" + jrex.getMessage());
		}
		catch(Exception ex){
			throw new JRException("Error evaluating query:" + ex.getMessage());
		}
		return ret;
	}
}