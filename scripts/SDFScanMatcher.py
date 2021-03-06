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
	def __init__(self, init_pose=np.identity(3), init_size=(10,10), discretization=0.5, k=2.0):
		self.map = SDFMap(init_size, discretization, k)
		self.pose = init_pose

	# finds the best alignment between the inputted scan and the map
	# adds the new scan to the map once an alignment is found
	# params:
	# - scan: the new scan's endpoints in the robot's frame of reference
	#		  2D numpy array with one point per row 
	#         (expressed in homogeneous coordinates)
	# - pose_delta_guess: an initial guess of the change in the robot's 
	#                     pose since the last scan
	# - max_iter: int, maximum number of Gauss-Newton iterations to use
	# - min_d_err: float, minimum change in error since last iteration to continue iterating
	def AddScan(self, scan, pose_delta_guess=np.identity(3), max_iter=100, min_d_err=1.0e-2):
		
		d_err = 1.0e4
		num_iter = 0

		est_pose = np.dot(self.pose,pose_delta_guess)

		# get residuals and jacobian for initial guess
		vals,J,grads = self.GetResidualAndJacobian(scan, est_pose)

		W = self.GetCauchyWeights(scan,vals,0.05)

		max_err = 1e-6
		#err = np.linalg.norm(vals**2)
		err = np.dot(np.dot(vals.T,W),vals)

		print("initial error: {:f}".format(err[0,0]))

		while num_iter < max_iter and abs(d_err) > min_d_err and np.max(J) > 0.0:

			# NOTE: need to add mechanism to stop if next estimate is worse

			# calculate pose update using Gauss-Newton with the Cauchy M-Estimator
			# still need to tune the estimator width parameter
			W = self.GetCauchyWeights(scan, vals, 0.05)

			#print('residual mean: {:f}   std dev: {:f}'.format(np.mean(vals),np.std(vals)))
			J_t_W = np.dot(J.T,W)
			delta_P = np.dot(np.linalg.inv(np.dot(J_t_W,J)),np.dot(J_t_W,vals))

			# calculate the Gauss-Newton pose update as x,y,gamma
			#delta_P = np.dot(np.linalg.inv(np.dot(J.T,J)),np.dot(J.T,vals))

			# convert to transformation matrix
			delta_P_mat = np.array([[math.cos(delta_P[2]), -math.sin(delta_P[2]), delta_P[0]*self.map.disc],
								    [math.sin(delta_P[2]),  math.cos(delta_P[2]), delta_P[1]*self.map.disc],
								    [                   0,                     0,           1]])

			new_pose = np.dot(est_pose, delta_P_mat)


			# reevaluate the residual
			print("pose at iteration {:d}: \n{:s}".format(num_iter,est_pose))
			
			vals,J,grads = self.GetResidualAndJacobian(scan, new_pose)
			#new_err = np.linalg.norm(vals**2)
			new_err = np.dot(np.dot(vals.T,W),vals)
			d_err = err - new_err[0,0]

			# stop iterating if new estimate increases error
			#if d_err < 0:
			#	print('stopping solver with error of {:f}'.format(new_err[0,0]))
			#	break
			#else:
			est_pose = new_pose

			err = new_err[0,0]

			print("error: {:f} \n".format(err))

			num_iter += 1

		# update the pose and map
		self.pose = est_pose
		self.map.UpdateMap(scan,self.pose)

	def GetCauchyWeights(self, scan, residuals, a):
		
		W = np.zeros((residuals.shape[0],residuals.shape[0]))
		c = 1.0 / a**2
		for i in range(residuals.shape[0]):
			W[i,i] = 1.0 / (1.0 + residuals[i,0]**2 * c)

		min_range = 1.0e4
		max_range = 0
		for endpoint in scan:
			r = np.linalg.norm(endpoint[:2])
			if r < min_range: min_range = r
			if r > max_range: max_range = r

		for i in range(len(scan)):
			r = np.linalg.norm(scan[i][:2])
			norm_r = ((r - min_range) / (max_range - min_range)) + 1.0
			W[i,i] = W[i,i] / norm_r
		return W

	# returns residual and jacobian for a given scan alignment
	# params:
	# - scan: numpy array, scan in the robot's frame, 1 endpoint per row 
	#         in homogeneous coordinates
	# - pose: numpy array, the robot's current estimated pose as a 3x3
	#         transformation matrix
	# returns:
	# - r:    numpy array, column vector of map residuals for each scan point
	# - J:    numpy array, stacked jacobians for each scan point, 1 per row
	def GetResidualAndJacobian(self, scan, pose):

		# transform points to global frame
		gf_scan = np.dot(scan,pose.T)

		# rearrange the rotation matrix to get its derivative
		dR = np.array([[pose[0,1], -pose[0,0]],
					   [pose[0,0],  pose[0,1]]])

		# assemble measurement and jacobian matrices 
		r = np.zeros((scan.shape[0],1))
		J = np.zeros((scan.shape[0],3))
		grads = np.zeros((scan.shape[0],2))
		partials = []
		for scan_idx in range(scan.shape[0]):

			# get map values and map gradients
			res,grad = self.map.GetMapValueAndGradient(gf_scan[scan_idx,:2])
			grads[scan_idx,:] = grad
			#print(res)
			#print(grad)
			#print()
			r[scan_idx,0] = res

			# get the partial derivative w.r.t. pose
			rot_part = np.dot(dR,np.expand_dims(scan[scan_idx,:2],0).T)
			partial = np.concatenate((np.identity(2),rot_part),axis=1)

			# get the map jacobian w.r.t pose
			J[scan_idx,:] = np.dot(grad,partial)

		return r,J,grads
