all:
	javac -cp "libs/*" -d classes src/*
	jar cf livestatus.jar -C classes .

clean:
	rm -rf classes/* 
