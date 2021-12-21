Setup for using/testing agent-receiver package

agent-receiver server is running in your site after omd start.
If you want to apply local changes:
    position yourself in agent-receiver directory
    f12

If you want to debug agent-receiver it's useful to run an uvicorn worker from the command line:
    omd stop agent-receiver
    uvicorn agent_receiver.server:app
