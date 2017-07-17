<?rsa version="1.0" encoding="utf-8"?>
<Configuration>
	<Product Id="Crypto-C ME">
		<Version>3.0.0.0</Version>
		<ReleaseDate>Apr 05 2008 19:24:39</ReleaseDate>
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
	<Signature URI="#ccme_base" Algorithm="FIPS140_INTEGRITY">MC0CFQCi9aO+5p/f2zz5YR+byru/YazcuwIUcmYPnrmvShqUoRxrmkFuv/xeJtk=</Signature>
	<Signature URI="#ccme_ecc" Algorithm="FIPS140_INTEGRITY">MC4CFQCe+8AbwW4tI2d2/Ze6afDhhICCJAIVAL/vfBevGgHOdeQAjjZzB9xjUQzy</Signature>
	<Signature URI="#ccme_eccaccel" Algorithm="FIPS140_INTEGRITY">MC0CFGvyJT729FBay1MA5eNzoHUD2i4mAhUAqREbgIGnF+QzuSZ3mgIaFGW7vOo=</Signature>
	<Signature URI="#ccme_eccnistaccel" Algorithm="FIPS140_INTEGRITY">MCwCFHfZwhM0Ax4e6AlXg1ZGAiYQuaDfAhQGZgJ3hmhjcRoaOUQpsIGcav6ZZg==</Signature>
	<Signature URI="#master" Algorithm="FIPS140_INTEGRITY">MC0CFQDBcdwmByrls8O4BBrYBVwWE7pCOwIUJX2nE0xRhxCOFXPNvQEKs80ZK7o=</Signature>
	<Signature URI="#Crypto-C ME" Algorithm="FIPS140_INTEGRITY">MC0CFD0W28kmo6qUEkkYDz11bPiWsxxMAhUArmrDio1OmX/HsGDbjfBtRcZRcoI=</Signature>
	<Signature URI="#runtime" Algorithm="FIPS140_INTEGRITY">MCwCFHVyUU2VPmoemImDeTPdQyncTGUGAhQOo/8BJQEAs5FQ0JQ7LW7L9TpOvw==</Signature>
</Configuration>

