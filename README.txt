This project installs HTML as user interface to python projects using WEB sockets. 
Output is event driven and could be designed without Java-Script.

1. Download and unzip the project 
2. Set environment PYTHONPATH=<download>/EezzServer/webroot/applications/EezzServer
3. Execute 
    python3 server.py --webroot=<download>/EezzServer/webroot --host=localhost --websocket=8000

4. Start the browser
    http://localhost:8000
    http://localhost:8000/esptest.html
    http://localhost:8000/esptree.html
    
See documentation in <download>/EezzServer/webroot/repository
=> Fast access to huge data sets using virtual tables
=> Fast development: No framework, no JavaScript, strictly decoupling UI and app-implementation
=> Recursive trees could be defined on HTML-<table> structure, 
   just by setting CSS styles class:eezzTreeNode and class:eezzTreeLeaf
