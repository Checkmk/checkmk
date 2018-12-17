FROM jenkins/jenkins:2.138.3

USER root
RUN addgroup --gid 131 docker \
    && usermod -a -G docker jenkins \
    && apt-get update \
    && apt-get -y install apt-transport-https \
    ca-certificates \
    curl \
    gnupg2 \
    software-properties-common \
    && curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg > /tmp/dkey; apt-key add /tmp/dkey \
    && add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") $(lsb_release -cs) stable" \
    && apt-get update \
    && apt-get -y install docker-ce \
    && rm -rf /var/lib/apt/lists/*
USER jenkins

RUN /usr/local/bin/install-plugins.sh \
	script-security:1.44 \
	email-ext:2.62 \
	jquery-detached:1.2.1 \
	token-macro:2.5 \
	monitoring:1.72.0 \
	resource-disposer:0.8 \
	cppcheck:1.21 \
	throttle-concurrents:2.0.1 \
	mailer:1.21 \
	display-url-api:2.2.0 \
	ant:1.8 \
	branch-api:2.0.20 \
	credentials:2.1.16 \
	multiple-scms:0.6 \
	matrix-auth:2.2 \
	violation-columns:1.6 \
	apache-httpcomponents-client-4-api:4.5.5-2.1 \
	docker-workflow:1.17 \
	pipeline-stage-tags-metadata:1.2.9 \
	workflow-step-api:2.15 \
	jquery-ui:1.0.2 \
	ldap:1.20 \
	jobConfigHistory:2.18 \
	gerrit-trigger:2.27.5 \
	pipeline-graph-analysis:1.6 \
	chucknorris:1.1 \
	workflow-basic-steps:2.7 \
	pipeline-input-step:2.8 \
	compress-artifacts:1.10 \
	run-condition:1.0 \
	pipeline-model-declarative-agent:1.1.1 \
	icon-shim:2.0.3 \
	claim:2.15 \
	pipeline-build-step:2.7 \
	htmlpublisher:1.16 \
	pipeline-rest-api:2.10 \
	conditional-buildstep:1.3.6 \
	momentjs:1.1.1 \
	plain-credentials:1.4 \
	copy-project-link:1.5 \
	global-build-stats:1.5 \
	ace-editor:1.1 \
	pipeline-stage-view:2.10 \
	workflow-cps-global-lib:2.9 \
	jackson2-api:2.8.11.3 \
	workflow-multibranch:2.19 \
	windows-slaves:1.3.1 \
	reverse-proxy-auth-plugin:1.6.3 \
	ws-cleanup:0.34 \
	jdk-tool:1.0 \
	pipeline-milestone-step:1.3.1 \
	ssh-slaves:1.26 \
	warnings:4.67 \
	analysis-core:1.95 \
	dry:2.50 \
	javadoc:1.4 \
	workflow-job:2.21 \
	translation:1.16 \
	violations:0.7.11 \
	scm-api:2.2.7 \
	workflow-cps:2.53 \
	xunit:1.103 \
	changes-since-last-success:0.5 \
	build-timeout:1.19 \
	ssh-agent:1.15 \
	docker-commons:1.13 \
	pipeline-model-extensions:1.2.9 \
	handlebars:1.1.1 \
	structs:1.14 \
	project-inheritance:2.0.0 \
	depgraph-view:0.13 \
	gravatar:2.1 \
	durable-task:1.22 \
	workflow-api:2.27 \
	jquery:1.12.4-0 \
	greenballs:1.15 \
	git:3.9.1 \
	authentication-tokens:1.3 \
	external-monitor-job:1.7 \
	jsch:0.1.54.2 \
	workflow-scm-step:2.6 \
	command-launcher:1.2 \
	antisamy-markup-formatter:1.5 \
	git-server:1.7 \
	cloudbees-folder:6.4 \
	pipeline-stage-step:2.3 \
	pam-auth:1.3 \
	bouncycastle-api:2.16.3 \
	workflow-support:2.18 \
	junit:1.24 \
	ssh-credentials:1.13 \
	workflow-durable-task-step:2.19 \
	promoted-builds:3.2 \
	maven-plugin:3.1.2 \
	subversion:2.10.6 \
	mapdb-api:1.0.9.0 \
	git-client:2.7.2 \
	parameterized-trigger:2.35.2 \
	pipeline-model-definition:1.2.9 \
	credentials-binding:1.16 \
	workflow-aggregator:2.5 \
	pipeline-model-api:1.2.9 \
	rebuild:1.28 \
	matrix-project:1.13
