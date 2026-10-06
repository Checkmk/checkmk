node {
    sh("""
	make all  
        echo ${
            params.A
        }	
""")
    print("done")
}
