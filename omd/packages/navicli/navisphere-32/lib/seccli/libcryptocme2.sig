<?rsa version="1.0" encoding="utf-8"?>
<Configuration>
	<Product Id="Crypto-C ME">
		<Version>3.0.0.0</Version>
		<ReleaseDate>Apr 05 2008 19:24:26</ReleaseDate>
		<ExpDate>""</ExpDate>
		<Copyright>
			Copyright (C) RSA
		</Copyright>
		<Library Id="master">cryptocme2</Library>
	</Product>
	<Runtime Id="runtime">
		<LoadOrder>
			<Library Id="ccme_base">ccme_base</Library>
			<Library Id="ccme_ecc">ccme_ecc</Library>
			<Library Id="ccme_eccaccel">ccme_eccaccel</Library>
			<Library Id="ccme_eccnistaccel">ccme_eccnistaccel</Library>
		</LoadOrder>
		<StartupConfig>
			<SelfTest>OnLoad</SelfTest>
		</StartupConfig>
	</Runtime>
	<Signature URI="#ccme_base" Algorithm="FIPS140_INTEGRITY">MC4CFQCNHCx7L/DuOPZVGdwhe1cdgwioAwIVALtJk59eXb4oNNgF4KW7wxtDYp/2</Signature>
	<Signature URI="#ccme_ecc" Algorithm="FIPS140_INTEGRITY">MC0CFGkCqu9PZNdTHY4HITw3qjSa/4ExAhUAj7B/IERPge0nggK7FC62T6nKCF8=</Signature>
	<Signature URI="#ccme_eccaccel" Algorithm="FIPS140_INTEGRITY">MCwCFGzyX31LxotPg3g42NNjAWbseq3FAhQMBX+pRv+/t/2xehwLskqid5Q7QA==</Signature>
	<Signature URI="#ccme_eccnistaccel" Algorithm="FIPS140_INTEGRITY">MCwCFCl3f9PwPLB+RUH4Bg6uR2B9Tu1AAhQ4bGOfMkXbHOsmjmfy6y/g07VJ/Q==</Signature>
	<Signature URI="#master" Algorithm="FIPS140_INTEGRITY">MCwCFA7P7iWMRRwstsbbPTBfePkumF1yAhR4k4q7OprVDj2iCixTu764ne6JHA==</Signature>
	<Signature URI="#Crypto-C ME" Algorithm="FIPS140_INTEGRITY">MC0CFQCH28dJVhOmXXx5SN6hrTtO2gwoLAIUEcg5XLMR7Pu9Ca/fYwJym6aQaVQ=</Signature>
	<Signature URI="#runtime" Algorithm="FIPS140_INTEGRITY">MCwCFCJZwEy6qsvarVfznt2kTcpBPQc6AhQ6nMHgYacgsvpTABB+50WBd2t8aQ==</Signature>
</Configuration>

