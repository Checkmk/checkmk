package livestatus;

import java.util.Map;
import net.sf.jasperreports.engine.JRDataset;
import net.sf.jasperreports.engine.JRException;
import net.sf.jasperreports.engine.query.JRQueryExecuter;
import net.sf.jasperreports.engine.query.JRQueryExecuterFactory;

public class LivestatusQueryExecuterFactory implements JRQueryExecuterFactory{
	@SuppressWarnings("rawtypes")
	public JRQueryExecuter createQueryExecuter(JRDataset dataset, Map parameters)
			throws JRException {
		return new LivestatusQueryExecuter(dataset, parameters);
	}

	public Object[] getBuiltinParameters() {
		return null;
	}

	public boolean supportsQueryParameterType(String arg0) {
		return false;
	}
}
