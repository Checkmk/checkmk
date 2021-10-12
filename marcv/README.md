Setup for using/testing marcv package

marcv server is running in your site after omd start.
If you want to apply local changes:
    position yourself in marcv directory
    f12

If you want to debug marcv it's useful to run an uvicorn worker from the command line:
    omd stop marcv
    uvicorn marcv.server:app
