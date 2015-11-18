/* ------------------------------------------------------------------------------- */
/* Client WEB-Socket implementation                                                */
/* ------------------------------------------------------------------------------- */
/* Variable declaration is generated by agent:
 * var gSocketAddr     = "ws://{}:{}";
 * var eezzWebSocket   = new WebSocket(gSocketAddr);
 * var eezzArguments   = "";
 */  
window.onload = eezzConnect();

function eezzConnect() {
	eezzWebSocket   = new WebSocket(gSocketAddr);
    var xEezzStatus = document.getElementsByName( 'eezzStatus' );
    
    if (xEezzStatus.length > 0) {
    	xEezzStatus[0].innerHTML = 'connected';
    }
    
    eezzWebSocket.onopen = function() { 
        var aParser   = document.createElement('a');
        aParser.href  = document.URL;
        var aJson     = {"path": aParser.pathname, "args": eezzArguments};                
        
        eezzWebSocket.send(JSON.stringify(aJson));
    }
    
    /* Error handling: Reopen connection */
    /* --------------------------------- */
    eezzWebSocket.onerror = function(aError) {   
        if (xEezzStatus.length > 0) {
        	xEezzStatus[0].innerHTML = 'disconnected: <button onclick="eezzConnect()">reconnect</button>';
        }
    }

    /* Wait for the application and update the document          */
    /* - updateValues transfer values within the document        */
    /* - update inserts values calculated by application         */
    /* --------------------------------------------------------- */
    eezzWebSocket.onmessage = function(aEvent) {
        var aJson = eval("(" + aEvent.data + ")");              

        var xDestination;
        var xSource;

        var xValElement;
        var xDstElement;
        var xDstAttribute;

        var xSrcElement;
        var xSrcAttribute;
        
        var xValue;
        
        /* update fragments: transfer values within document */
        for (xKeyElement in aJson.updateValue) {
            xValElement   = decodeURIComponent( aJson.updateValue[xKeyElement] );
            
            xDestination  = xKeyElement.split(".");
            xSource       = xValElement.split('.')
            
            if (xDestination.length != 2) {
            	continue;
            }
            
            xDstElement   = document.getElementsByName( xDestination[0] );
            xDstAttribute = xDestination[1];
            
            if (xDstElement.length == 0) {
            	continue;
            }
            
            if (xSource.length != 2) {
            	continue;
            }
            xSrcElement   = document.getElementsByName(xSource[0]);
            xSrcAttribute = xSource[1];
            
            if (xSrcElement.length == 0) {
            	continue;
            }
            
            xValue = xSrcElement[0].getAttribute(xSrcAttribute);
            if (xValue != undefined) {
            	xDstElement[0].setAttribute(xDstAttribute, xValue);
            }
        }

        /* update fragments: insert values */
        for (xKeyElement in aJson.update) {
            xValElement   = decodeURIComponent( aJson.update[xKeyElement] );

            xDestination  = xKeyElement.split(".");
            
            if (xDestination.length < 2) {
            	continue;
            }
            xDstElement   = document.getElementsByName( xDestination[0] );
            xDstAttribute = xDestination[1];
            
            if (xDstElement.length == 0) {
            	continue;
            }
            
            if (xDstAttribute == 'style') {
            	if (xDestination.length > 2) {
            		xDstElement[0].style[xDestination[2]] = xValElement;
            	}
            	continue;
            }
            
            if (xDstElement[0].getAttribute('class') == 'eezzTreeNode') {
            	eezzTreeInsert(xDestination[2], xValElement);
            	break;
            }
            else {
                if (xDstAttribute == 'innerHTML') {
                	xDstElement[0].innerHTML = xValElement;
                }
                else {
                	xDstElement[0].setAttribute(xDstAttribute, xValElement);
                }
            }
        }    
    	
        /* Start reading files */
        if (aJson.files) {
            readFiles(aJson);
        }
    }     
}

/* --------------------------------- */
/* --------------------------------- */
function eezzTreeExCo(aElement) {
	var xExpanded = aElement.getAttribute('eezz-tree-expanded');	
	if (xExpanded == 'expanded') {
		var aTreeNodeHdr = aElement.getElementsByTagName('thead')
		for (i = 0; i < aTreeNodeHdr.length; i++) {
			aElement.innerHTML = aTreeNodeHdr[i].innerHTML;
			break;
		}
		aElement.setAttribute('eezz-tree-expanded', 'collapsed');
		return false;
	}
	else if (xExpanded == undefined) {
		aElement.setAttribute('eezz-tree-expanded', 'collapsed');
		return true;
	}
	else if (xExpanded == 'expanded') {
		aElement.setAttribute('eezz-tree-expanded', 'collapsed');
		return true;
	}
	else {
		return true;
	}
}

/* --------------------------------- */
/* --------------------------------- */
function eezzTreeInsert(aElementId, aNodeElement) {
	// Find tree node by id tag element tr
	var aElement     = document.getElementById(aElementId)
	var xExpanded    = aElement.getAttribute('eezz-tree-expanded');	

	if (xExpanded == 'expanded') {
		eezzTreeExCo(aElement);
	}
	if (aElementId == 'id000000') {
		aElement.innerHTML = aNodeElement;
		return;
	}
	// Save the header
	var aTreeNodeHdr = aElement.innerHTML;
	
	// The new element should take the entire place
	var aCols = aElement.getElementsByTagName('td').length.toString()
	// Clear element for new entry
	aElement.innerHTML = '';

	// Create a new entry
	var xTd     = document.createElement('td');
	var xTable  = document.createElement('table');
    var xTHead  = document.createElement('thead');
    var xTBody  = document.createElement('tbody');

    xTable.setAttribute('class', 'eezzTreeNode');
    xTBody.setAttribute('class', 'eezzTreeNode');
    xTHead.setAttribute('class', 'eezzTreeNode');
    xTd.setAttribute('class', 'eezzTreeNode');
    xTd.setAttribute('colspan', aCols);
    xTd.appendChild(xTable);
    xTable.appendChild(xTHead);
    xTable.appendChild(xTBody);
    xTHead.innerHTML = aTreeNodeHdr
    xTBody.innerHTML = aNodeElement
        
    aElement.appendChild(xTd);
    aElement.setAttribute('eezz-tree-expanded', 'expanded');
}

/* Read one file in chunks           */
/* --------------------------------- */
function readOneFile(aHeader, aFile) {
    var aChunkSize = aHeader.chunkSize;    
    var aSequence  = 0;
    
    for (var i = 0; i < aFile.size; i += aChunkSize) {
        (function(xHeader, xFile, xStart) {
            var aCurrentChunk = Math.min(aChunkSize, xFile.size - xStart);  
            
            var aReader = new FileReader();
            var aBlob   = xFile.slice(xStart, xStart + aChunkSize);
            var xJson   = xHeader;
            
            xJson.file.start     = xStart;
            xJson.file.chunkSize = aCurrentChunk;
            xJson.file.sequence  = aSequence;
            
            aReader.onloadend  = (
                function(xOneJson) {
                    return function(e) {
                    };
                } )(xJson);


            aReader.onprogress  = (
                function(xOneJson) {
                    return function(e) {
                    };
                } )(xJson);
            
            aReader.onload   = (
                function(xOneJson) {
                    var xResponse = JSON.stringify(xOneJson);                                
                    return function(e) {
                        eezzWebSocket.send(xResponse);
                        eezzWebSocket.send(e.target.result);
                    };
                } )(xJson);
            
            aReader.readAsArrayBuffer(aBlob);
        } )(aHeader, aFile, i);
        aSequence += 1;
    }
}

/* Read files                        */
/* --------------------------------- */
function readFiles(aHeader) {
    asyncFileCnt      = 0;
    
    for (var i = 0; i < aHeader["files"].length; i++) {
        aElem       = document.getElementsByName(aHeader["files"][i]["source"])[0];
        var xFile   = aElem.files[0];
        var xReader = new FileReader();
        
        var xJson   = {
            "file": { 
                "chunkSize": xFile.size,
                "size"     : xFile.size, 
                "name"     : xFile.name,
                "source"   : aHeader["files"][i]["source"],
                "type"     : aHeader["files"][i]["type"]
            }, 
            "reader"   :  aHeader.reader,
            "update"   :  aHeader["files"][i]["update"],
            "progress" :  aHeader["files"][i]["progress"],
            "chunkSize":  aHeader.chunkSize
            };
       
        readOneFile(xJson, xFile);
    }
}            

/* Process easy click events         */
/* --------------------------------- */
function easyClick(aEvent, aElement) {
    var aJStr  = decodeURIComponent(aElement.getAttribute("data-eezz-event"));
    var aJson  = eval("(" + aJStr + ")"); 
    var aDest;
    var aElem;
    var aPost  = false;
    var aValue;
    var aChunkSize = 65536*2;

    aJson['name'] = aElement['name'];
        
    if (aJson.files) {
        aJson['return'] = {code:0, values:[]};
        aJson.chunkSize = aChunkSize;
        aPost = true;
    }

    /* Generate a callback request */
    if (aJson.callback) {    
        aPost = true;
	    for (xMethod in aJson.callback) {
	        for (xArg in aJson.callback[xMethod]) {
	            aDest = aJson.callback[xMethod][xArg];
	            
	            if (typeof aDest === 'string' && aDest.indexOf(".") >= 0) {
	                aDest = aJson.callback[xMethod][xArg].split("."); 
	            
	                if (aDest[0] == "this") {
	                    aJson.callback[xMethod][xArg] = aElement.getAttribute(aDest[1]);
	                }
	                else {
	                    aElem  = document.getElementsByName(aDest[0])[0];
	                    aValue = aElem[aDest[1]]
	                    if (aValue === undefined) {
	                        aValue = aElem.getAttribute(aDest[1]);
	                    }
	                    aJson.callback[xMethod][xArg] = aValue;
	                }
	            }
	            else {
	                aJson.callback[xMethod][xArg] = aDest;
	            }                        
	        }
	    }
    }

    /* transfer a value from one element to another                */
    /* eezz-agent sets updateValue, if it can't find this property */
    if (aJson.updateValue) {
    	for (xSource in aJson.updateValue) {
    		aSrc     = xSource.split(".")
    		aSrcElem = document.getElementsByName( aSrc[0] );
    		
    		if (aSrcElem.length > 0) {
    			aValue  = aSrcElem[0].getAttribute( aSrc[1] );
    		}
    	}
    }
    
    if (aJson.update) {
    	aPost = true;
    }

    if (aElement.getAttribute('class') == 'eezzTreeNode') {
    	aPost = eezzTreeExCo(aElement);
    	if (aEvent.stopPropagation) {
    		aEvent.stopPropagation();
    	}
    	else {
    		aEvent.cancelBubble();
    	}
    }
    
    if (aPost == true) {
        var aResponse = JSON.stringify(aJson);
        eezzWebSocket.send(aResponse);
    } 
}
