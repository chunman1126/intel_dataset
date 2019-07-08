'''
SDFScanMatcher.py
 - Andrew Kramer

Creates an SDF map from inputted 2 dimensional laser scans based 
on the method presented in:

    Fossel, Joscha-David & Tuyls, Karl & Sturm, Jurgen. (2015). 
    2D-SDF-SLAM: A signed distance function based SLAM frontend 
    for laser scanners. 1949-1955. 10.1109/IROS.2015.7353633. 

Finds the best alignment between new scans and the map using 
Gauss-Newton optimization, then updates the map with the aligned scan.

'''

import numpy as np 
import math
from SDFMap import SDFMap

class SDFScanMatcher:

	# initializes the SDF map and sets its initial size
	def __init__(self, init_pose=np.identity(3), init_size=(20,20), discretization=0.5, k=2.0):
		self.map = SDFMap(init_size, discretization, k)
		self.pose = init_pose
