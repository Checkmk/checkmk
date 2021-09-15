Setup for using/testing marcv package

If you want to run marcv server in your dev environment:
    scripts/run-pipenv run uvicorn marcv.server:app

If you want to run marcv server in your site:
    position yourself in marcv directory
    f12
    python3 -m gunicorn -k uvicorn.workers.UvicornWorker marcv.server:app (run with a site user)

