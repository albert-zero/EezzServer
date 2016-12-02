/**
 *  Copyright (C) 2015  Albert Zedlitz
 *  
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *  
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *  
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

// Collect the sceen
function doCollect(xElement) {
    var i;
    var xElemDescr = {
    	'id'          : '',
        'children'    : [],       // list of children 
    	'parent'      : {},       // parent element
        'view'        : [0, 0, xElement.clientWidth, xElement.clientHeight], // left, top, right, bottom
        'position'    : [xElement.clientLeft,  xElement.clientTop, 0], 		 // x, y, phi
        'velocity'    : [0,0,0],  // v(x),   v(y),   v(phi) == omega
        'acceleration': [0,0,0],  // v(x,t), v(y,t), v(phi, t)
        'friction'    : [0,0,0,0] // f(v(x)), f(v(y)), f(omega), f(omega, velocity)
    }
    
    if (xElement.getAttribute('data-eezz-animation')) {
    	xElemDescr['id'] = xElement.id;
    }
    
    for (i = 0; i < xElement.childNodes.length; i++) {    	
    	if (xElement.childNodes[i].getAttribute == undefined) {
            continue;
        }
    	var xChildNode  = xElement.childNodes[i];
    	var xChildDescr = doCollect(xChildNode);        	
    	xChildDescr['parent'] = xElemDescr;
    	// A child will be free to move araound in the parents view:
    	xChildDescr['view'] = [ 0, 0, 
    	                        Math.max( 1, xElement.clientWidth  - xChildNode.clientWidth  ),
    	                        Math.max( 1, xElement.clientHeight - xChildNode.clientHeight ) ];
    }
	return xElemDescr;	
}

// Handle a frame and move all elements
function onPlayFrame(xTime, xParent, xToMove) {
	for (var i = 0; i < xParent['animation']['children'].length; i++) {
		onPlayFrame(xTime, xParent, xToMove);

		var xElem = document.getElementById( xAttr['id'] );
		if (xElem == null) {
			continue;
		}
		xAttr = xParent['animation']['children'][0];

	    xAttr['position'][0] += xAttr['velocity'][0];
	    xAttr['position'][1] += xAttr['velocity'][1];
	    xAttr['position'][2] += xAttr['velocity'][3];
	    
	    xAttr['velocity'][0] += xAttr['acceleration'][0];
	    xAttr['velocity'][1] += xAttr['acceleration'][1];
	    
	    // correlation to friction
	    xAttr['velocity'][0] -= xAttr['velocity'][0] * Math.max(0, Math.min(1, xAttr['friction'][0]));
	    xAttr['velocity'][1] -= xAttr['velocity'][0] * Math.max(0, Math.min(1, xAttr['friction'][1]));
	    xAttr['rotation'][1] -= xAttr['rotation'][1] * Math.max(0, Math.min(1, xAttr['friction'][2]));            	
	
	    // correlation of speed and rotation:
	    //--xParentSpeed = Math.sqrt( Math.pow(xParent['velocity'][0], 2) + Math.pow(xParent['velocity'][1], 2) );
	    //--xOwnSpeed    = Math.sqrt( Math.pow(  xAttr['velocity'][0], 2) + Math.pow(  xAttr['velocity'][1], 2) );
	    //--xAttr['rotation'][1] += ( xParentSpeed + xOwnSpeed ) * xAttr['friction'][3]; 
	    
		
		// border detection
	    if (xAttr['position'][0] < xAttr['view'][0] || 
	        xAttr['position'][1] < xAttr['view'][1] ||
	        xAttr['position'][0] > xAttr['view'][2] ||
	        xAttr['position'][1] > xAttr['view'][3]) {
	            continue;
	    }
	    xToMove ++;
		xElem.style.left = xAttr['position'][0] + 'px';
	    xElem.style.top  = xAttr['position'][1] + 'px';
	    xElem.style.transform = 'rotate(' + xAttr['rotation'][0] + 'deg)';
	}
}   

// Request loop which terminates, if either ther are no elements to move or 
// number of frames comitted.
function onPlay(xTime, xParent) {
	var xToMove = 0;
	
	onPlayFrame(xTime, xParent, xToMove);
	
	if ( xToMove > 0 ) {
		if ( xParent['animation']['frames'] == -1) {
			requestAnimationFrame(function(timestamp){ onPlay(timestamp, xParent); });			
		} 
		else if (xParent['animation']['frames'] > 0 ) {
			xParent['animation']['frames'] -= 1;
			requestAnimationFrame(function(timestamp){ onPlay(timestamp, xParent); });			
		}
	}
}

