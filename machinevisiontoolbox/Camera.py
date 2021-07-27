#!/usr/bin/env python
"""
Camera class
@author: Dorian Tsai
@author: Peter Corke
"""
from math import pi, sqrt, sin, tan
from abc import ABC, abstractmethod
import copy

import numpy as np
import matplotlib.pyplot as plt
import scipy

import cv2 as cv
from spatialmath import base, Line3
from machinevisiontoolbox.base import idisp


# from machinevisiontoolbox.classes import Image
# import CameraVisualizer as CamVis

# from mpl_toolkits.mplot3d import Axes3D, art3d
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# from collections import namedtuple
from spatialmath import SE3
import spatialmath.base as smb

class Camera(ABC):

    # list of attributes
    _name = []      # camera  name (string)
    _camtype = []   # camera type (string)

    _imagesize = None        # number of pixels (horizontal, vertical)
    _pp = None        # principal point (horizontal, vertical)
    _rhou = []      # pixel imagesize (single pixel) horizontal
    _rhov = []      # pixel imagesize (single pixel) vertical
    _image = []     # image (TODO image class?), for now, just numpy array

    _T = []         # camera pose (homogeneous transform, SE3 class)

    _ax = []        # for plotting, axes handle

    def __init__(self,
                 name=None,
                 camtype='central',
                 rho=10e-6,
                 imagesize=(1024, 1024),
                 pp=None,
                 noise=None,
                 pose=None,
                 limits=None,
                 labels=None):
        """
        Create instance of a Camera class
        """
        if name is None:
            self._name = camtype
        else:
            if not isinstance(name, str):
                raise TypeError(name, 'name must be a string')
            self._name = name

        if not isinstance(camtype, str):
            raise TypeError(camtype, 'camtype must be a string')
        self._camtype = camtype

        rho = base.getvector(rho)
        if len(rho) == 1:
            self._rhou = rho[0]
            self._rhov = rho[0]
        elif len(rho) == 2:
            self._rhou = rho[0]
            self._rhov = rho[1]
        else:
            raise ValueError(rho, 'rho must be a 1- or 2-element vector')

        self._pp = pp

        self.imagesize = imagesize

        if pose is None:
            self._pose = SE3()
        else:
            self._pose = SE3(pose)

        self._noise = noise

        self._image = None

        self._ax = None

        self._distortion = None
        self.labels = labels
        self.limits = limits

    def __str__(self):
        # TODO, imagesize should be integers
        s = ''
        self.fmt = '{:>15s}: {}\n'
        s += self.fmt.format('Name', self.name + ' [' + self.__class__.__name__ + ']')
        s += self.fmt.format('pixel size', ' x '.join([str(x) for x in self.rho]))
        s += self.fmt.format('image size', ' x '.join([str(x) for x in self.imagesize]))
        s += self.fmt.format('pose', self.pose.printline(file=None, fmt="{:.3g}"))
        return s

    def __repr__(self):
        return str(self)
        
    @abstractmethod
    def project_point(self, P, **kwargs):
        pass

    def project_line(self, *args, **kwargs):
        raise NotImplementedError('not implemented for this camera model')

    def project_conic(self, *args, **kwargs):
        raise NotImplementedError('not implemented for this camera model')

    @property
    def name(self):
        """
        Get camera name

        :return: camera name
        :rtype: str

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.name
        """
        return self._name

    @name.setter
    def name(self, newname):
        """
        Set camera name

        :param newname: camera name
        :type newname: str
        """
        if isinstance(newname, str):
            self._name = newname
        else:
            raise TypeError(newname, 'name must be a string')

    @property
    def camtype(self):
        """
        Get camera type

        :return: camera projection type
        :rtype: str

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.camtype
        """
        return self._camtype

    @camtype.setter
    def camtype(self, newcamtype):
        """
        Set camera type

        :param newcamtype: camera projection type
        :type newcamtype: str
        """
        if isinstance(newcamtype, str):
            self._camtype = newcamtype
        else:
            raise TypeError(newcamtype, 'camtype must be a string')

    @property
    def imagesize(self):
        """
        Get size of image plane

        :return: image plane size (width, height)
        :rtype: ndarray(2)

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.imagesize

        :seealso: :meth:`.width` :meth:`.height` :meth:`.nu` :meth:`.nv`
        """
        return self._imagesize

    @imagesize.setter
    def imagesize(self, npix):
        """
        Set image plane size

        :param npix: [description]
        :type npix: array_like(2)
        :raises ValueError: bad value

        Sets the size of the virtual image plane.
        
        .. note:: If the principle point is not set, then it
            is set to the centre of the image plane.

        :seealso: :meth:`.width` :meth:`.height` :meth:`.nu` :meth:`.nv`
        """
        npix = base.getvector(npix)
        if len(npix) == 1:
            self._imagesize = np.r_[npix[0], npix[0]]
        elif len(npix) == 2:
            self._imagesize = npix
        else:
            raise ValueError(
                npix, 'imagesize must be a 1- or 2-element vector')
        if self._pp is None:
            self._pp = self._imagesize / 2

    @property
    def nu(self):
        """
        Get image plane width

        :return: width
        :rtype: int

        Number of pixels in the u-direction (width)

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.nu

        :seealso: :meth:`.nv` :meth:`.width`
        """
        return self._imagesize[0]

    @property
    def nv(self):
        """
        Get image plane height

        :return: height
        :rtype: int

        Number of pixels in the v-direction (height)

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.nv

        :seealso: :meth:`.nu` :meth:`.height`
        """
        return self._imagesize[1]

    @property
    def width(self):
        """
        Get image plane width

        :return: width
        :rtype: int

        Image plane height, number of pixels in the v-direction

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.width

        :seealso: :meth:`.nu` :meth:`.height`
        """
        return self._imagesize[0]

    @property
    def height(self):
        """
        Get image plane height

        :return: height
        :rtype: int

        Image plane width, number of pixels in the u-direction

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.height

        :seealso: :meth:`.nv` :meth:`.width`
        """
        return self._imagesize[1]

    @property
    def pp(self):
        """
        Get principal point coordinate

        :return: principal point
        :rtype: ndarray(2)

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.pp

        :seealso: :meth:`.u0` :meth:`.v0`
        """
        return self._pp

    @pp.setter
    def pp(self, pp):
        """
        Set principal point coordinate

        :param pp: principal point
        :type pp: array_like(2)

        :seealso: :meth:`.pp` :meth:`.u0` :meth:`.v0`
        """
        pp = base.getvector(pp)
        if len(pp) == 1:
            self._pp = np.r_[pp[0], pp[0]]
        elif len(pp) == 2:
            self._pp = pp
        else:
            raise ValueError(pp, 'pp must be a 1- or 2-element vector')

    @property
    def u0(self):
        """
        Get principal point: horizontal coordinate

        :return: horizontal component of principal point
        :rtype: float

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.u0

        :seealso: :meth:`.v0` :meth:`.pp`
        """
        return self._pp[0]

    @property
    def v0(self):
        """
        Get principal point: vertical coordinate

        :return: vertical component of principal point
        :rtype: float

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.v0

        :seealso: :meth:`u0` :meth:`pp`
        """
        return self._pp[1]

    @property
    def rhou(self):
        """
        Get pixel size: horizontal value

        :return: horizontal pixel size
        :rtype: float

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.rhou

        :seealso: :meth:`.rhov` :meth:`.rho`
        """
        return self._rhou

    # this is generally the centre of the image, has special meaning for
    # perspective camera
    
    @property
    def rhov(self):
        """
        Get pixel size: horizontal value

        :return: horizontal pixel size
        :rtype: float

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.rhov

        :seealso: :meth:`.rhov` :meth:`.rho`
        """
        return self._rhov

    @property
    def rho(self):
        """
        Get pixel dimensions

        :return: horizontal pixel size
        :rtype: ndarray(2)

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.rhov

        :seealso: :meth:`.rhou` :meth:`.rhov`
        """

        return np.array([self._rhou, self._rhov])

    # @property
    # def image(self):
    #     return self._image

    # @image.setter
    # def image(self, newimage):
    #     """


    #     :param newimage: [description]
    #     :type newimage: [type]
    #     """
    #     self._image = Image(newimage)

    @property
    def pose(self):
        """
        Get camera pose

        :return: pose of camera frame
        :rtype: SE3

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.pose

        :seealso: :meth:`.move`
        """
        return self._pose

    @pose.setter
    def pose(self, newpose):
        """
        Set camera pose

        :param newpose: pose of camera frame
        :type newpose: SE3 or ndarray(4,4)

        :seealso: :meth:`.move`
        """
        self._pose = SE3(newpose)

    @property
    def noise(self):
        return self._noise

    def move(self, T, name=None):
        """
        Move camera

        :param T: pose of camera frame
        :type T: SE3
        :return: new camera object
        :rtype: Camera instance

        Returns a copy of the camera object with pose set to ``T``.

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera();
            >>> camera.move(SE3(0.1, 0.2, 0.3)

        .. note:: The ``plot`` method of this cloned camera will create a new
            window.

        :seealso: :meth:`.pose`
        """

        newcamera = copy.copy(self)
        if name is not None:
            newcamera.name = name
        else:
            newcamera.name = self.name + "-moved"
        newcamera._ax = None
        newcamera.pose = T
        return newcamera

    # ----------------------- plotting ----------------------------------- #

    def _plotcreate(self, fig=None, ax=None):
        """
        Create plot window for camera image plane

        :param fig: figure to plot into, defaults to None
        :type fig: figure handle, optional
        :param ax: axis to plot into, defaults to None
        :type ax: 2D axis handle, optional
        :return: figure and axis
        :rtype: (fig, axis)

        Creates a 2D axis that represents the image plane of the virtual
        camera.

        :seealso: :meth:`plot` :meth:`mesh`
        """

        if self._ax is not None:
            return

        if (fig is None) and (ax is None):
            # create our own handle for the figure/plot
            print('creating new figure and axes for camera')
            fig, ax = plt.subplots()  # TODO *args, **kwargs?
        # TODO elif ax is a plot handle, else raise ValueError
        # else:

        if self._image is not None:
            # if camera has an image, display said image
            idisp(self._image,
                      fig=fig,
                      ax=ax,
                      title=self._name,
                      drawonly=True)
        else:
            if self.limits is None:
                ax.set_xlim(0, self.nu)
                ax.set_ylim(0, self.nv)
            else:
                ax.set_xlim(self.limits[0], self.limits[1])
                ax.set_ylim(self.limits[2], self.limits[3])
            ax.autoscale(False)
            ax.invert_yaxis()
            ax.grid(True)
            if self.labels is None:
                ax.set_xlabel('u (pixels)')
                ax.set_ylabel('v (pixels)')
            else:
                ax.set_xlabel(self.labels[0])
                ax.set_ylabel(self.labels[1])
            ax.set_title(self.name)
            ax.set_facecolor('lightyellow')
            ax.figure.canvas.set_window_title('Machine Vision Toolbox for Python')

        # TODO figure out axes ticks, etc
        self._ax = ax
        return fig, ax  # likely this return is not necessary

    def clf(self):
        """
        Clear the virtual image plane

        Remove all points and lines from the image plane.
        """
        for artist in self._ax.get_children():
            try:
                artist.remove()
            except:
                pass

    def plot_point(self, P, *fmt, objpose=None, pose=None, **kwargs):
        """
        Plot points on the virtual image plane

        :param P: 3D world points or 2D image plane points
        :type P: ndarray(3,), ndarray(3,N), or ndarray(2,), ndarray(2,N)
        :param objpose: transformation for the wireframe points, defaults to None
        :type objpose: SE3, optional
        :param pose: pose of the camera, defaults to None
        :type pose: SE3, optional
        :param args: additional arguments passed to ``plot``
        :param kwargs: additional arguments passed to ``plot``
        :return: image plane points
        :rtype: ndarray(2,N)

        3D world points are first projected to the image plane
        Points are organized as columns of the arrays.

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera()
            >>> camera.plot_point([0.2, 0.3, 2])
            >>> camera.plot_point([0.2, 0.3, 2], 'r*')
            >>> camera.plot_point([0.2, 0.3, 2], pose=SE3(0.1, 0, 0))

        :seealso: :meth:`Camera.project_point`
        """
        self._plotcreate()

        if not isinstance(P, np.ndarray):
            P = base.getvector(P)

        if P.shape[0] == 3:
            # plot world points
            p = self.project_point(P, pose=pose, objpose=objpose)
        else:
            p = P

        if p.shape[0] != 2:
            raise ValueError('p must have be (2,), (3,), (2,n), (3,n)')

        self._ax.plot(p[0, :], p[1, :], *fmt, **kwargs)
        plt.show()

        return p

    def homline(self, l, *args, **kwargs):
        # get handle for this camera image plane
        self._plotcreate()
        plt.autoscale(False)

        base.plot_homline(l, *args, ax=self._ax, **kwargs)

    def disp(self, im, **kwargs):
        """
        Display image on virtual image plane

        :param im: image to display
        :type im: Image instance
        :param kwargs: options to ``idisp()``

        :seealso: :meth:`machinevisiontoolbox.idisp()`
        """
        self._plotcreate()
        im.disp(ax=self._ax, title=False, **kwargs)
        self.imagesize = (im.shape[1], im.shape[0])
        self._ax.set_xlim(0, self.nu)
        self._ax.set_ylim(self.nv,0)
        plt.autoscale(False)

    def plot_wireframe(self, X, Y, Z, *fmt, objpose=None, pose=None, **kwargs):
        """
        Plot 3D wireframe in virtual image plane

        :param X: world X coordinates
        :type X: ndarray(N,M)
        :param Y: world Y coordinates
        :type Y: ndarray(N,M)
        :param Z: world Z coordinates
        :type Z: ndarray(N,M)
        :param objpose: transformation for the wireframe points, defaults to None
        :type objpose: SE3, optional
        :param pose: pose of the camera, defaults to None
        :type pose: SE3, optional
        :param kwargs: arguments passed to ``plot``

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera, mkcube
            >>> camera = CentralCamera()
            >>> X, Y, Z = mkcube(0.2, pose=SE3(0, 0, 1), edge=True)
            >>> camera.plot_wireframe(X, Y, Z, 'k--')

        """

        # self._ax.plot_surface(X, Y, Z)
        # plt.show()
   
        # check that mesh matrices conform
        if X.shape != Y.shape or X.shape != Z.shape:
            raise ValueError('matrices must be the same shape')
        
        if pose is None:
            pose = self.pose
        if objpose is not None:
            pose = objpose.inv() * pose
        
        # get handle for this camera image plane
        self._plotcreate()
        plt.autoscale(False)
        
        # draw 3D line segments
        nsteps = 21
        s = np.linspace(0, 1, nsteps)

        # c.clf
        # holdon = c.hold(1);
        
        for i in range(X.shape[0]-1):      # i=1:numrows(X)-1
            for j in range(X.shape[1]-1):  # j=1:numcols(X)-1
                P0 = np.r_[X[i, j], Y[i, j], Z[i, j]]
                P1 = np.r_[X[i+1, j], Y[i+1, j], Z[i+1, j]]
                P2 = np.r_[X[i, j+1], Y[i, j+1], Z[i, j+1]]
                
                if self.camtype == 'perspective':
                    # straight world lines are straight on the image plane
                    uv = self.project_point(np.c_[P0, P1], pose=pose)
                else:
                    # straight world lines are not straight, plot them piecewise
                    P = (1 - s) * P0[:, np.newaxis] + s * P1[:, np.newaxis]
                    uv = self.project_point(P, pose=pose)

                self._ax.plot(uv[0, :], uv[1, :], *fmt, **kwargs)
                
                if self.camtype == 'perspective':
                    # straight world lines are straight on the image plane
                    uv = self.project_point(np.c_[P0, P2], pose=pose)
                else:
                    # straight world lines are not straight, plot them piecewise
                    P = (1 - s) * P0[:, np.newaxis] + s * P2[:, np.newaxis]
                    uv = self.project(P, pose=pose)

                self._ax.plot(uv[0, :], uv[1, :], *fmt, **kwargs)

        
        for j in range(X.shape[1]-1):  # j=1:numcols(X)-1
            P0 = [X[-1,j],   Y[-1,j],   Z[-1,j]]
            P1 = [X[-1,j+1], Y[-1,j+1], Z[-1,j+1]]
            
            # if c.perspective
                # straight world lines are straight on the image plane
            uv = self.project_point(np.c_[P0, P1], pose=pose);
            # else
            #     # straight world lines are not straight, plot them piecewise
            #     P = bsxfun(@times, (1-s), P0) + bsxfun(@times, s, P1);
            #     uv = c.project(P, 'setopt', opt);
            self._ax.plot(uv[0,:], uv[1,:], *fmt, **kwargs)
        
        # c.hold(holdon); # turn hold off if it was initially off

        plt.draw()

    def plot_camera(self, pose=None, scale=1, shape='frustum', label=True,
                    alpha=1, solid=False, color='r', projection='ortho',
                    ax=None):
        """
        Plot 3D camera icon in world view

        :param pose: camnera pose
        :type pose: SE3
        :param scale: scale factor, defaults to 1
        :type scale: float
        :param shape: icon shape: 'frustum' [default], 'camera'
        :type shape: str, optional
        :param label: [description], defaults to True
        :type label: bool, optional
        :param alpha: [description], defaults to 1
        :type alpha: int, optional
        :param solid: [description], defaults to False
        :type solid: bool, optional
        :param color: [description], defaults to 'r'
        :type color: str, optional
        :param projection: projection model for new axes
        :type projection: str, optional
        :param ax: axes to draw in, defaults to current 3D axes
        :type ax: Axes3D, optional
        :return: [description]
        :rtype: [type]
        """

        # if (fig is None) and (ax is None):
        #     # create our own handle for the figure/plot
        #     print('creating new figure and axes for camera')
        #     fig = plt.figure()
        #     ax = fig.gca(projection='3d')
        #     # ax.set_aspect('equal')

        """[summary]
        face order -x, +y, +x, -y
        """
        # get axes to draw in
        ax = smb.axes_logic(ax, 3, projection=projection)

        if pose is None:
            pose = self.pose

        # draw camera-like object:
        if shape == 'frustum':
            # TODO make this kwargs or optional inputs
            # side colors:
            #  +x red
            #  -y red
            #  +y green
            #  -y yellow
            length = scale
            widthb = scale/10
            widtht = scale
            widthb /= 2
            widtht /= 2
            b0 = np.array([-widthb, -widthb, 0, 1])
            b1 = np.array([-widthb, widthb, 0, 1])
            b2 = np.array([widthb, widthb, 0, 1])
            b3 = np.array([widthb, -widthb, 0, 1])
            t0 = np.array([-widtht, -widtht, length, 1])
            t1 = np.array([-widtht, widtht, length, 1])
            t2 = np.array([widtht, widtht, length, 1])
            t3 = np.array([widtht, -widtht, length, 1])

            # bottom/narrow end
            T = pose.A
            b0 = (T @ b0)[:-1]
            b1 = (T @ b1)[:-1]
            b2 = (T @ b2)[:-1]
            b3 = (T @ b3)[:-1]

            # wide/top end
            t0 = (T @ t0)[:-1]
            t1 = (T @ t1)[:-1]
            t2 = (T @ t2)[:-1]
            t3 = (T @ t3)[:-1]

            # Each set of four points is a single side of the Frustrum
            # points = np.array([[b0, b1, t1, t0], [b1, b2, t2, t1], [
            #                   b2, b3, t3, t2], [b3, b0, t0, t3]])
            points = [
                np.array([b0, b1, t1, t0]),  # -x face
                np.array([b1, b2, t2, t1]),  # +y face
                np.array([b2, b3, t3, t2]),  # +x face
                np.array([b3, b0, t0, t3])   # -y face
            ]
            poly = Poly3DCollection(points,
                                    facecolors=['r', 'g', 'r', 'y'],
                                    alpha=alpha)
            ax.add_collection3d(poly)

        elif shape == 'camera':

            # the box is centred at the origin and its centerline parallel to the
            # z-axis.  Its z-extent is -bh/2 to bh/2.
            W = 0.5       # width & height of the box
            L = 1.2       # length of the box
            cr = 0.2       # cylinder radius
            ch = 0.4       # cylinder height
            cn = 12        # number of facets of cylinder
            a = 3          # length of axis line segments

            # draw the box part of the camera
            smb.plot_box3d(sides=np.r_[W, W, L] * scale, pose=pose, solid=solid, color=color, alpha=0.5)

            # draw the lens
            smb.plot_cylinder(radius=cr * scale, height=np.r_[L / 2, L / 2 + ch] * scale, resolution=cn, pose=pose, solid=solid, color=color, alpha=0.5)

            if label:
                ax.set_xlabel('x')
                ax.set_ylabel('y')
                ax.set_zlabel('z')

        return ax

    def add_noise_distortion(self, uv):
        # distort the pixels
        
        # add Gaussian noise with specified standard deviation
        if self.noise is not None:
            uv += np.random.normal(0.0, self.noise, size=uv.shape)
        return uv 

class CentralCamera(Camera):
    """
    Central projection camera class
    """

    def __init__(self,
                 f=8*1e-3,
                 distortion=None,
                 **kwargs):
        """
        Create central camera projection model

        :param f: focal length, defaults to 8*1e-3
        :type f: float, optional
        :param distortion: camera distortion parameters, defaults to None
        :type distortion: array_like(5), optional

        :seealso: :meth:`.distort`
        """

        super().__init__(camtype='perspective', **kwargs)
        # TODO some of this logic to f and pp setters
        self.f = f

        self._distortion = distortion


    def __str__(self):
        s = super().__str__()
        s += self.fmt.format('principal pt', self.pp)
        s += self.fmt.format('focal length', self.f)

        return s


    def project_point(self, P, pose=None, objpose=None, behind=True, visibility=False, **kwargs):
        r"""
        Project 3D points to image plane

        :param P: 3D points to project into camera image plane
        :type P: array_like(3), array_like(3,n)
        :param pose: camera pose with respect to the world frame, defaults to
            camera's ``pose`` attribute
        :type pose: SE3, optional
        :param objpose:  3D point reference frame, defaults to world frame
        :type objpose: SE3, optional
        :param visibility: test if points are visible, default False
        :type visibility: bool
        :return: image plane points
        :rtype: ndarray(2,n)

        Project a 3D point to the image plane

        .. math::

            \hvec{p} = \mat{C} \hvec{P}

        where :math:`\mat{C}` is the camera calibration matrix and :math:`\hvec{p}` and :math:`\hvec{P}`
        are the image plane and world frame coordinates respectively.

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera()
            >>> camera.project_point((0.3, 0.4, 2))

        If ``pose`` is specified it is used for the camera frame pose, otherwise
        the attribute ``pose``.  The object's ``pose`` attribute is not updated
        if ``pose`` is specified.

        A single point can be specified as a 3-vector, multiple points as an
        array with three rows and one column (x, y, z) per point.

        The points ``P`` are by default with respect to the world frame, but 
        they can be transformed by specifying ``objpose``.
        
        If world points are behind the camera, the image plane points are set to
        NaN.
        
        if ``visibility`` is True then each projected point is checked to ensure
        it lies in the bounds of the image plane.  In this case there are two
        return values: the image plane coordinates and an array of booleans
        indicating if the corresponding point is visible.
        """
        if pose is None:
            pose = self.pose

        C = self.C(pose)

        if isinstance(P, np.ndarray):
            if P.ndim == 1:
                P = P.reshape((-1, 1))  # make it a column
        else:
            P = base.getvector(P, out='col')

        # make it homogeneous if not already
        if P.shape[0] == 3:
            P = base.e2h(P)

        # project 3D points

        if objpose is not None:
            P = objpose.A @ P

        x = C @ P

        if behind:
            x[2, x[2, :] < 0] = np.nan  # points behind the camera are set to NaN

        x = base.h2e(x)

        # add Gaussian noise and distortion
        x = self.add_noise_distortion(x)

        #  do visibility check if required
        if visibility:
            visible = ~np.isnan(x[0,:]) \
                & (x[0, :] >= 0) \
                & (x[1, :] >= 0) \
                & (x[0, :] < self.nu) \
                & (x[1, :] < self.nv)
            
            return x, visible
        else:
            return x

    def project_line(self, lines):
        r"""
        Project 3D lines to image plane

        :param line: Plucker lines
        :type line: Line3 instance with N values
        :return: 2D homogeneous lines, one per column
        :rtype: ndarray(3,N)

        The Line3 object can contain multiple lines.  The result array has one
        column per line, and each column in a vector describing the image plane
        line in homogeneous form :math:`\ell_0 u + \ell_1 v + \ell_2 = 0`.

        The projection is

        .. math::

            \ell = \vex{\mat{C} \sk{\vec{L}} \mat{C}^T}

        where :math:`\mat{C}` is the camera calibration matrix and :math:`\sk{\vec{L}}`
        is the skew matrix representation of the Plucker line.

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> from spatialmath import Line3
            >>> line = Line3.TwoPoints((-3, -4, 5), (5, 2, 6))
            >>> print(line)
            >>> camera = CentralCamera()
            >>> camera.project_line(line)

        :seealso: :class:`spatialmath.Line3`
        """
        if not isinstance(lines, Line3):
            raise ValueError('expecting Line3 lines')
        # project Plucker lines

        lines2d = []
        for line in lines:
            l = base.vex( self.C() @ line.skew @ self.C().T)
            x = l / np.max(np.abs(l))  # normalize by largest element
            lines2d.append(x)
        return np.column_stack(lines2d)

    def project_conic(self, conic):
        r"""
        Project 3D conic to image plane

        :param conic: conic matrix :math:`\mat{A}`
        :type conic: ndarray(4,4)
        :return: image plane conic
        :rtype: ndarray(3,3)

        .. math::

            a = \mat{C} \mat{A} \mat{C}^T

        """
        if not smb.ismatrix(conic, (4,4)):
            raise ValueError('expecting 4x4 conic matrix')

        return self.C() @ conic @ self.C().T

    def plot_epiline(self, F, p, *fmt, **kwargs):
        r"""
        Plot epipolar line

        :param F: fundamental matrix
        :type F: ndarray(3,3)
        :param p: image plane point
        :type p: array_like(2) or ndarray(2,N)
        :param fmt: line style argument passed to ``plot``
        :param kwargs: additional line style arguments passed to ``plot``
    
        Plot the epipolar line induced by the image plane points ``p``.  Each
        line is given by

        .. math::

            \ell = \mat{F} \fvec[1]{p}

        which is in homogeneous form :math:`\ell_0 u + \ell_1 v + \ell_2 = 0`
        and the conjugate point :math:`\fvec[2]{p}` lies on this line.

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> from spatialmath import SE3
            >>> camera1 = CentralCamera(name='camera1')
            >>> camera2 = camera1.move(SE3(0.1, 0.05, 0), name='camera2')
            >>> P = [-0.2, 0.3, 5]  # world point
            >>> p = camera1.project_point(P)  # project to first camera
            >>> camera2.plot_point(P, 'kd') # project and display in second camera
            >>> camera2.plot_epiline(camera1.F(camera2), p) # plot epipolar line in second camera

        :seealso: :meth:`pyplot.plot`
        """
        # p is 3 x N, result is 3 x N
        self.homline((F @ base.e2h(p)).T, *fmt, **kwargs)

    def plucker(self, points):
        """
        Project image plane points to Plucker lines

        :param points: set of image plane points
        :type points: ndarray(2,N)
        :return: set of corresponding Plucker lines
        :rtype: Line3 instance with ``N`` values

        For each image plane point compute the equation of a Plucker line
        that represents the ray in 3D space.

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import Camera
            >>> camera = CentralCamera()
            >>> line = camera.plucker((100, 200))
            >>> print(line)

        :reference:  "Multiview Geometry", Hartley & Zisserman, p.162

        :seealso: :class:`Line3`
        """
        # define Plucker line in terms of point (centre of camera) and direction
        C = self.C()
        Mi = np.linalg.inv(C[:3, :3])
        v = C[:, 3]
        lines = []
        for point in points.T:
            lines.append(Line3.PointDir(-Mi @ v, Mi @ smb.e2h(point)))
        return Line3(lines)

    def fov(self):
        """
        Camera field-of-view angles

        :return: field of view angles in radians
        :rtype: ndarray(2)
        
        ``C.fov()`` are the field of view angles (2x1) in radians for the camera x and y
        (horizontal and vertical) directions.
        """
        try:
            return 2 * np.arctan(np.r_[self.imagesize] / 2 * np.r_[self.rho] / self.f)
        except:
            raise ValueError('imagesize or rho properties not set')

    def _distort(self, X):
        """
        CentralCamera.distort Compute distorted coordinate
        
        Xd = cam.distort(X) is the projected image plane point X (2x1) after 
        lens distortion has been applied.
        """
        
        # convert to normalized image coordinates
        X = np.linalg.inv(self.K) * X

        # unpack coordinates
        u = X[0, :]
        v = X[1, :]

        # unpack distortion vector
        k = self.distortion[:3]
        p = self.distortion[3:]

        r = np.sqrt(u ** 2 + v ** 2) # distance from principal point
        
        # compute the shift due to distortion
        delta_u = u * (k[0] * r ** 2 + k[1] * r ** 4 + k[2] * r ** 6) + \
            2 * p[0] * u * v + p[1] * (r ** 2 + 2 * u ** 2)
        delta_v = v  * (k[0] * r ** 2 + k[1] * r ** 4 + k[2] * r ** 6) + \
            p[0] * (r ** 2 + 2 * v ** 2) + 2  *p[1] * u * v
        
        # distorted coordinates
        ud = u + delta_u
        vd = v + delta_v
        
        return self.K * smb.e2h( np.r_[ud, vd] ) # convert to pixel coords

    @property
    def fu(self):
        """
        Get focal length in horizontal direction

        :return: focal length in horizontal direction
        :rtype: 2-tuple

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera(name='camera1')
            >>> camera.fu

        :seealso: :meth:`.fv` :meth:`.f`
        """
        return self._fu

    @property
    def fv(self):
        """
        Get focal length in vertical direction

        :return: focal length in horizontal direction
        :rtype: 2-tuple

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera(name='camera1')
            >>> camera.fv

        :seealso: :meth:`.fu` :meth:`.f`
        """
        return self._fv

    @property
    def f(self):
        """
        Get focal length

        :return: focal length in horizontal and vertical directions
        :rtype: 2-tuple

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera(name='camera1')
            >>> camera.f

        :seealso: :meth:`.fu` :meth:`.fv`
        """
        return (self._fu, self._fv)

    @f.setter
    def f(self, f):
        """[summary]

        :param f: focal length
        :type f: scalar or array_like(2)
        :raises ValueError: incorrect length of ``f``
        """
        f = base.getvector(f)

        if len(f) == 1:
            self._fu = f[0]
            self._fv = f[0]
        elif len(f) == 2:
            self._fu = f[0]
            self._fv = f[1]
        else:
            raise ValueError(f, 'f must be a 1- or 2-element vector')

    @property
    def K(self):
        """
        Intrinsic matrix of camera

        :return: intrinsic matrix
        :rtype: ndarray(3,3)

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera(name='camera1')
            >>> camera.K

        :seealso: :meth:`.C`
        """
        # fmt: off
        K = np.array([[self.fu / self.rhou, 0,                   self.u0],
                      [ 0,                  self.fv / self.rhov, self.v0],
                      [ 0,                  0,                    1]
                      ], dtype=np.float)
        # fmt: on
        return K

    # =================== camera calibration =============================== #
    def C(self, T=None):
        """
        Camera projection matrix

        :param T: camera pose, defaults to pose from camera object
        :type T: SE3, optional
        :return: camera projection/calibration matrix
        :rtype: ndarray(3,4)

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera(name='camera1')
            >>> camera.C()
            >>> camera.C(SE3(0.1, 0, 0))
            >>> camera.move(SE3(0.1, 0, 0)).C()

        .. note:: Pose is that of the camera frame with respect to the world
            frame.

        :seealso: :meth:`.K`
        """
        P0 = np.eye(3, 4)
        if T is None:
            T = self.pose
        return self.K @ P0 @ T.inv().A

    @staticmethod
    def points2C(P, p):
        """
        Camera calibration from data points

        :param P: calibration points in world coordinate frame
        :type P: ndarray(3,N)
        :param p: calibration points in image plane
        :type p: ndarray(2,N)
        :return: camera calibration matrix and residual
        :rtype: ndarray(3,4), float

        ``C, r = camcald(P, p)`` is the camera matrix (3x4) determined by least
        squares from corresponding world ``P`` and image-plane ``p`` points.
        Corresponding points are represented by corresponding columns of ``P``
        and ``p``.

        .. note:: This method assumes no lense distortion affecting the image plane
            coordinates.

        :seealso: :meth:`Camera.CentralCamera`
        """
        z4 = np.zeros((4,))

        A = np.empty(shape=(0,11))
        b = np.empty(shape=(0,))
        for uv, X in zip(p.T, P.T):
            u, v = uv
            # fmt: off
            row = np.array([
                    np.r_[ X, 1, z4, -u * X],
                    np.r_[z4, X,  1, -v * X]
                ])
            # fmt: on
            A = np.vstack((A, row))
            b = np.r_[b, uv]

        # solve Ax = b where c is 11 elements of camera matrix
        c, *_ = scipy.linalg.lstsq(A, b)

        # compute and print the residual
        r = A @ c - b

        c = np.r_[c, 1]   # append a 1
        C = c.reshape((3,4))  # make a 3x4 matrix

        return C, r

    @classmethod
    def decomposeC(cls, C):
        """
        Decompose camera calibration matrix

        :param C: camera calibration matrix
        :type C: ndarray(3,4)
        :return: camera model
        :rtype: CentralCamera instance

        Decompose, or invert, a 3x4 camera calibration matrix ``C``.
        The result is a ``CentralCamera`` instance with the following parameters set:

        ================  ====================================
        Parameter         Meaning
        ================  ====================================
        ``f``             focal length in pixels
        ``sx``, ``sy``    pixel size where ``sx``=1
        (``u0``, ``v0``)  principal point
        ``pose``          pose of the camera frame wrt world
        ================  ====================================

        Example:

        .. runblock:: pycon

            >>> from machinevisiontoolbox import CentralCamera
            >>> camera = CentralCamera(name='camera1')
            >>> C = camera.C(SE3(0.1, 0, 0))
            >>> CentralCamera.decomposeC(C)

        .. note:: Since only :math:`f s_x` and :math:`f s_y` can be estimated we
            set :math:`s_x = 1`.

        :reference:	Multiple View Geometry, Hartley&Zisserman, p 163-164

        :seealso: :meth:`.C` :meth:`points2C`
        """
        def rq(S):
            # from vgg_rq.m
            # [R,Q] = vgg_rq(S)  Just like qr but the other way around.
            # If [R,Q] = vgg_rq(X), then R is upper-triangular, Q is orthogonal, and X==R*Q.
            # Moreover, if S is a real matrix, then det(Q)>0.
            # By awf

            S = S.T
            Q, U = np.linalg.qr(S[::-1, ::-1])
            Q = Q.T
            Q = Q[::-1, ::-1]
            U = U.T
            U = U[::-1, ::-1]

            if np.linalg.det(Q) < 0:
                U[:, 0] = -U[:, 0]
                Q[0, :] = -Q[0, :]
            return U, Q


        if not C.shape == (3,4):
            raise ValueError('argument is not a 3x4 matrix')

        u, s, v = np.linalg.svd(C)
        v = v.T

        # determine camera position
        t = v[:, 3]  # last column
        t = t / t[3]
        t = t[:3]

        # determine camera orientation
        M = C[:3, :3]
        K, R = rq(M)

        # deal with K having negative elements on the diagonal
        # make a matrix to fix this, K*C has positive diagonal
        C = np.diag(np.sign(np.diag(K)))
        
        # now  K*R = (K*C) * (inv(C)*R), so we need to check C is a proper rotation
        # matrix.  If isn't then the situation is unfixable
        
        if not np.isclose(np.linalg.det(C), 1):
            raise RuntimeError('cannot correct signs in the intrinsic matrix')
        
        # all good, let's fix it
        K = K @ C
        R = C.T @ R
        
        # normalize K so that lower left is 1
        K = K / K[2, 2]
        
        # pull out focal length and scale factors
        f = K[0, 0]
        s = np.r_[1, K[1,1] / K[0, 0]]

        # build an equivalent camera model
        return cls(name='invC',
            f=f, pp=K[:2, 2], rho=s, pose=SE3.Rt(R.T, t))

# https://docs.opencv.org/3.1.0/d9/d0c/group__calib3d.html#gaaae5a7899faa1ffdf268cd9088940248

    # ======================= homography =============================== #

    def H(self, T, N, d):
        """
        Compute homography from plane and camera poses

        :param T: relative camera motion
        :type T: SE3
        :param N: plane normal with respect to world frame
        :type N: array_like(3)
        :param d: plane offset from world frame origin
        :type d: float
        :return: homography matrix
        :rtype: ndarray(3,3)

        Computes the homography matrix for the camera observing a plane from two
        viewpoints. The first view is from the current camera pose
        (``self.pose``), and the second is after a relative motion represented
        by the rigid-body motion ``T``. The plane has normal ``N`` and at
        distance ``d``.
        """

        if d < 0:
            raise ValueError(d, 'plane distance d must be > 0')

        N = base.getvector(N)
        if N[2] < 0:
            raise ValueError(N, 'normal must be away from camera (N[2] >= 0)')

        # T transform view 1 to view 2
        T = SE3(T).inv()

        HH = T.R + 1.0 / d * T.t @ N  # need to ensure column then row = 3x3

        # apply camera intrinsics
        HH = self.K @ HH @ np.linalg.inv(self.K)

        return HH / HH[2, 2]  # normalised

    @staticmethod
    def points2H(p1, p2, method, **kwargs):
        """
        Compute homography from corresponding points

        :param p1: image plane points
        :type p1: ndarray(2,N)
        :param p2: image plane points
        :type p2: ndarray(2,N)
        :param method: algorithm 'leastsquares', 'ransac', 'lmeds', 'prosac'
        :type method: str
        :param kwargs: optional arguments as required for ransac', 'lmeds'
            methods
        :return: homography, residual and optional inliers
        :rtype: ndarray(3,3), float, ndarray.bool(N)

        :seealso: `cv2.findHomography <https://docs.opencv.org/master/d9/d0c/group__calib3d.html#ga4abc2ece9fab9398f2e560d53c8c9780>`_
        """

        points2H_dict = {
            'leastsquares': 0,
            'ransac': cv.RANSAC,
            'lmeds': cv.LMEDS,
            'prosac': cv.RHO 
        }

        H, mask = cv.findHomography(
            srcPoints=p1.T,
            dstPoints=p2.T,
            method=points2H_dict[method],
            **kwargs)
        
        return H, mask.flatten().astype(np.bool)

    # https://docs.opencv.org/3.1.0/d9/d0c/group__calib3d.html#ga7f60bdff78833d1e3fd6d9d0fd538d92
    def invH(self, H, K=None, ):
        """
        Decompose homography matrix

        ``self.invH(H)`` decomposes the homography ``H`` (3,3) into the camerea
        motion and the normal to the plane. In practice, there are multiple
        solutions and the return ``S``  is a named tuple with elements
        ``S.T``, the camera motion as a homogeneous transform matrix (4,4), and
        translation not to scale, and ``S.N`` the normal vector to the plawne
        (3,3).  # TODO why is the normal vector a 3x3?
        """

        if K is None:
            K = np.identity(3)
            # also have K = self.K

        H = np.linalg.inv(K) @ H @ K

        # normalise so that the second singular value is one
        U, S, V = np.linalg.svd(H, compute_uv=True)
        H = H / S[1, 1]

        # compute the SVD of the symmetric matrix H'*H = VSV'
        U, S, V = np.linalg.svd(np.transpose(H) @ H)

        # ensure V is right-handed
        if np.linalg.det(V) < 0:
            print('det(V) was < 0')
            V = -V

        # get squared singular values
        s0 = S[0, 0]
        s2 = S[2, 2]

        # v0 = V[0:, 0]
        # v1 = V[0:, 1]
        # v2 = V[0:, 2]

        # pure rotation - where all singular values == 1
        if np.abs(s0 - s2) < (100 * np.spacing(1)):
            print('Warning: Homography due to pure rotation')
            if np.linalg.det(H) < 0:
                H = -H
            # sol = namedtuple('T', T, ''
        # TODO finish from invhomog.m
        print('Unfinished')
        return False


    # =================== fundamental matrix =============================== #

    def F(self, other):
        """
        Fundamental matrix

        :param other: second camera view
        :type other: CentralCamera instance, SE3 or fundamental matrix
        :return: fundamental matrix
        :rtype: numpy(3,3)

        - ``C1.F(T)`` is the fundamental matrix relating two camera views.  The
          first view is from the current camera pose ``C.pose`` and the second
          is a relative motion represented by ``T``.

        - ``C1.F(C2)`` is the fundamental matrix relating two camera views
          described by camera objects ``C1`` (first view) and ``C2`` (second
          view).

        :reference:
        - Y.Ma, J.Kosecka, S.Soatto, S.Sastry, "An invitation to 3D",
            Springer, 2003. p.177
        
        :seealso: :meth:`.points2F` :meth:`.E`
        """

        if isinstance(other, SE3):
            E = self.E(other)
            K = self.K
            return np.linalg.inv(K).T @ E @ np.linalg.inv(K)

        elif isinstance(other, CentralCamera):
            # use relative pose and camera parameters of 
            E = self.E(other)
            K1 = self.K
            K2 = other.K
            return np.linalg.inv(K2).T @ E @ np.linalg.inv(K1)

        else:
            raise ValueError('bad type')

    @staticmethod
    def points2F(
                    p1,
                    p2,
                    method,
                    inliers=True,
                    **kwargs):
        """
        Compute fundamental matrix from corresponding points

        :param p1: image plane points
        :type p1: ndarray(2,N)
        :param p2: image plane points
        :type p2: ndarray(2,N)
        :param method: algorithm '7p', '8p', 'ransac', 'lmeds'
        :type method: str
        :param inliers: return a vector of inlier points
        :type inliers: bool
        :param kwargs: optional arguments as required for ransac', 'lmeds'
            methods
        :return: fundamental matrix and residual
        :rtype: ndarray(3,3), float

        ``CentralCamera.points2F(p1, p2)`` computes the fundamental matrix from
        two sets of corresponding image-plane points. Corresponding points are
        given by corresponding columns of ``p1`` and ``p2``.

        :seealso: `cv2.findFundamentalMat <https://docs.opencv.org/master/d9/d0c/group__calib3d.html#ga59b0d57f46f8677fb5904294a23d404a>`_
            :meth:`.F`  :meth:`.E`
        """
        
        points2F_dict = {
                '7p': cv.FM_7POINT,
                '8p': cv.FM_8POINT,
                'ransac': cv.FM_RANSAC,
                'lmeds': cv.FM_LMEDS}

        F, mask = cv.findFundamentalMat(p1.T, p2.T,
                                        method=points2F_dict[method],
                                        **kwargs)

        if mask is not None:
            mask = mask.flatten().astype(np.bool)
            p1 = p1[:, mask]
            p2 = p2[:, mask]

        elines = base.e2h(p2).T @ F # homog lines, one per row
        p1h = base.e2h(p1)
        residuals = []
        for i, line in enumerate(elines):
            d = line @ p1h[:, i] / np.sqrt(line[0] ** 2 + line[1] ** 2)
            residuals.append(d)
        resid = np.array(residuals).mean()

        if inliers:
            return F, resid, mask
        else:
            return F, resid

    # ===================== essential matrix =============================== #

    def E(self, other):
        """
        Essential matrix from two camera views

        :param other: second camera view
        :type other: CentralCamera instance, SE3 or fundamental matrix
        :return: essential matrix
        :rtype: numpy(3,3)

        - ``C1.E(C2)`` is the essential matrix relating two camera views
          described by camera objects ``C1`` (first view) and ``C2`` (second
          view).  Assumes the cameras have the same intrinsics.

        - ``C1.E(T)`` is the essential matrix relating two camera views.  The
          first view is from the current camera pose ``C1.pose`` and the second
          is a relative motion represented by the homogeneous transformation
          ``T``.
        
        - ``C1.E(F)`` is the essential matrix based on the fundamental matrix ``F`` (3x3)

        :reference:
            - Y.Ma, J.Kosecka, S.Soatto, S.Sastry, "An invitation to 3D",
              Springer, 2003. p.177

        :seealso: :meth:`.F` :meth:`.decomposeE` :meth:`.points2E`
        """

        if isinstance(other, np.ndarray) and other.shape == (3,3):
            # essential matrix from F matrix and intrinsics
            return self.K.T @ other @ self.K

        elif isinstance(other, CentralCamera):
            # camera relative pose
            T21 = other.pose.inv() * self.pose

        elif isinstance(other, SE3):
            # relative pose given explicitly
            T21 = other.inv()

        else:
            raise ValueError('bad type')
        
        return base.skew(T21.t) @ T21.R

    def points2E(self,
                    p1,
                    p2,
                    method=None,
                    K=None,
                    inliers=False,
                    *kwargs):
        """
        Essential matrix from points

        :param P1: image plane points
        :type P1: ndarray(2,N)
        :param P2: image plane points
        :type P2: ndarray(2,N)
        :param method: method, can be 'ransac' or 'lmeds'
        :type method: str
        :param K: camera intrinsic matrix, defaults to that of camera object
        :type K: ndarray(3,3), optional
        :param inliers: return a vector of inlier points
        :type inliers: bool
        :param kwargs: additional arguments required for 'ransac' or 'lmeds'
            options
        :return: essential matrix and optional inlier vevtor
        :rtype: ndarray(3,3), ndarray(N) of bool

        Compute the essential matrix from two sets of corresponding points.
        Each set of points is represented by the columns of the matrix ``P1``
        or ``P2``.

        :seealso: `cv2.findEssentialMat <https://docs.opencv.org/master/d9/d0c/group__calib3d.html#gad245d60e64d0c1270dbfd0520847bb87>`_

        """
        if K is None:
            K = self.K

        points2E_dict = {
            'ransac': cv.RANSAC,
            'lmeds': cv.LMEDS
        }
        if method is not None:
            method = points2E_dict[method]

        E, mask = cv.findEssentialMat(p1, p2, cameraMatrix=K, method=method, **kwargs)
        if inliers:
            return E, mask
        else:
            return E

    def decomposeE(self, E, P):
        """
        Decompose essential matrix

        :param E: essential matrix
        :type E: ndarray(3,3)
        :param P: world point or Match object to resolve ambiguity
        :type P: array_like(3) or Match
        :return: camera relative pose
        :rtype: SE3 instance

        Determines relative pose from essential matrix. This operation has
        multiple solutions which is resolved by passing in:

        - a single world point in front of the camera
        - a ``Match`` object

        :reference:
        - OpenCV: 
        
        :seealso: `cv2.decomposeEssentialMat <https://docs.opencv.org/master/d9/d0c/group__calib3d.html#ga54a2f5b3f8aeaf6c76d4a31dece85d5d>`_
            `cv2.recoverPose <https://docs.opencv.org/master/d9/d0c/group__calib3d.html#gadb7d2dfcc184c1d2f496d8639f4371c0>`_
            :meth:`Match`
        """

        if isinstance(P, np.ndarray):

            R1, R2, t = cv.decomposeEssentialMat(E=E)
            # not explicitly stated, but seems that this returns (R, t) from 
            # camera to world

            possibles = [(R1, t), (R1, -t), (R2, t), (R2, -t)]

            for Rt in possibles:
                pose = SE3.Rt(Rt[0], Rt[1]).inv()
                p = self.project_point(P, pose=pose, behind=True)
                # check if point is projected behind the camera, indicated
                # by nan values
                if not np.isnan(p[0]):
                    # return the first good one
                    return pose
        else:
            # passed a Match object
            match = P

            retval, R, t, mask = cv.recoverPose(
                    E=E,
                    points1=match.p1.T,
                    points2=match.p2.T,
                    cameraMatrix=self.C()[:3, :3]
                    )
            # not explicitly stated, but seems that this returns (R, t) from 
            # camera to world

            return SE3.Rt(R, t).inv()

    # ===================== image plane motion ============================= #


    def visjac_p(self, uv, Z):
        '''
        Image Jacobian (interaction matrix) for point features 
        
        Returns a 2Nx6 matrix of stacked Jacobians, one per image-plane point.
        uv is a 2xN matrix of image plane points
        Z  is the depth of the corresponding world points. Can be scalar, same distance to every
        point, or a vector or list of length N.
        
        References:
        * A tutorial on Visual Servo Control", Hutchinson, Hager & Corke, 
            IEEE Trans. R&A, Vol 12(5), Oct, 1996, pp 651-670.
        * Robotics, Vision & Control, Corke, Springer 2017, Chap 15.
        '''
        uv = base.getmatrix(uv, (2, None))

        Z = base.getvector(Z)
        if len(Z) == 1:
            Z = np.repeat(Z, uv.shape[1])
        elif len(Z) != uv.shape[1]:
                raise ValueError('Z must be a scalar or have same number of columns as uv')
            
        L = np.empty((0, 6))  # empty matrix

        K = self.K
        Kinv = np.linalg.inv(K)
        
        for z, p in zip(Z, uv.T):  # iterate over each column (point)

            # convert to normalized image-plane coordinates
            xy = Kinv @ base.e2h(p)
            x = xy[0,0]
            y = xy[1,0]

            # 2x6 Jacobian for this point
            # fmt: off
            Lp = K[:2,:2] @ np.array(
                [ [-1/z,  0,     x/z, x * y,      -(1 + x**2), y],
                  [ 0,   -1/z,   y/z, (1 + y**2), -x*y,       -x] ])
            # fmt: on
            # stack them vertically
            L = np.vstack([L, Lp])

        return L

    def flowfield(self, vel, Z=2):
        vel = base.getvector(vel, 6)

        u = np.arange(0, self.nu, 50)
        v = np.arange(0, self.nv, 50)
        [U,V] = np.meshgrid(u, v, indexing='ij')
        du = np.empty(shape=U.shape)
        dv = np.empty(shape=U.shape)
        for r in range(U.shape[0]):                      
            for c in range(U.shape[1]):
                J = self.visjac_p((U[r,c], V[r,c]), Z )            
                ud, vd =  J @ vel
                du[r,c] = ud
                dv[r,c] = -vd

        self._plotcreate()
        plt.quiver(U, V, du, dv, 0.4)
        plt.show(block=True)


    def estpose(self, P, p, method='iterative'):

        method_dict = {
            'iterative': cv.SOLVEPNP_ITERATIVE,
            'epnp': cv.SOLVEPNP_EPNP,
            'p3p': cv.SOLVEPNP_P3P,
            'ap3p': cv.SOLVEPNP_AP3P,
            'ippe': cv.SOLVEPNP_IPPE,
            'ippe-square': cv.SOLVEPNP_IPPE_SQUARE,
        }

        sol = cv.solvePnP(P.T, p.T, self.K, self._distortion, flags=method_dict[method])
        
        if sol[0]:
            return SE3(sol[2]) * SE3.EulerVec(sol[1])
        else:
            return None

    def derivatives(self, x, P):
        #compute Jacobians and projection

        from  machinevisiontoolbox.camera_derivatives import cameraModel
        
        Kp = [self.f[0], self.rhou, self.rhov, self.u0, self.v0]

        return cameraModel(*x, *P, *Kp)
# ------------------------------------------------------------------------ #

class FishEyeCamera(Camera):
    """
    Fish eye camera class

    This camera model assumes central projection, that is, the focal point
    is at z=0 and the image plane is at z=f.  The image is not inverted.

    :seealso: :class:`Camera`
    """

    def __init__(self, k=None, projection='equiangular', **kwargs):
        r"""
        Fisheye camera object

        :param k: scale factor
        :type k: float, optional
        :param projection: projection model: ``'equiangular'`` [default], ``'sine'``, ``'equisolid'`` or ``'stereographic'``
        :type projection: str, optional

        The elevation angle range is from :math:`-pi/2` (below the mirror) to
        maxangle above the horizontal plane. The mapping from elevation angle
        :math:`\theta` to image plane radius is given by:

            =============   =======================================
            Projection      :math:`r(\theta)`
            =============   =======================================
            equiangular     :math:`r = k \theta`
            sine            :math:`r = k \sin \theta`
            equisolid       :math:`r = k \sin \frac{\theta}{2}`
            stereographic   :math:`r = k \tan \frac{\theta}{2}`
            =============   =======================================

        .. note:: If K is not specified it is computed such that the circular
          imaging region maximally fills the square image plane.
        
        :seealso: :class:`~machinevisiontoolbox.Camera.Camera` :class:`~machinevisiontoolbox.Camera.CentralCamera`
            :class:`~machinevisiontoolbox.Camera.CatadioptricCamera` :class:`~machinevisiontoolbox.Camera.SphericalCamera`
        """

        super().__init__(camtype='fisheye', **kwargs)

        self.projection = projection

        if k is None:
            r = np.min((self.imagesize - self.pp) * self.rho)

        if self.projection == 'equiangular':
            if k is None:
                k = r / (pi/2)
            rfunc = lambda theta: k * theta
        elif self.projection == 'sine':
            if k is None:
                k = r
            rfunc = lambda theta: k * np.sin(theta)
        elif self.projection == 'equisolid':
            if k is None:
                k = r / sin(pi / 4)
            rfunc = lambda theta: k * np.sin(theta / 2)
        elif self.projection == 'stereographic':
            if k is None:
                k = r / tan(pi / 4)
            rfunc = lambda theta: k * np.tan(theta / 2)
        else:
            raise ValueError('unknown projection model')

        self.k = k
        self.rfunc = rfunc
        
    def __str__(self):
        s = super().__str__()
        s += self.fmt.format('model', self.projection, fmt="{}")
        s += self.fmt.format('k', self.k, fmt="{:.4g}")
        return s        
        
    def project_point(self, P, pose=None, objpose=None):
        """
        Project 3D points to image plane

        :param P: 3D points to project into camera image plane
        :type P: array_like(3), array_like(3,n)
        :param pose: camera pose with respect to the world frame, defaults to
            camera's ``pose`` attribute
        :type pose: SE3, optional
        :param objpose:  3D point reference frame, defaults to world frame
        :type objpose: SE3, optional
        :param visibility: test if points are visible, default False
        :type visibility: bool
        :raises ValueError: [description]
        :return: image plane points
        :rtype: ndarray(2,n)

        The elevation angle range is from :math:`-pi/2` (below the mirror) to
        maxangle above the horizontal plane. The mapping from elevation angle
        :math:`\theta` to image plane radius is given by:

            =============   =======================================
            Projection      :math:`r(\theta)`
            =============   =======================================
            equiangular     :math:`r = k \theta`
            sine            :math:`r = k \sin \theta`
            equisolid       :math:`r = k \sin \frac{\theta}{2}`
            stereographic   :math:`r = k \tan \frac{\theta}{2}`
            =============   =======================================
        
        World points are projected to the image plane and represented
        by columns, each column is the u- and v-coordinate.

        If ``pose`` is specified it is used for the camera pose instead of the
        attribute ``pose``.  The object's attribute is not updated.

        The points ``P`` are by default with respect to the world frame, but 
        they can be transformed by specifying ``objpose``.
        """
        
        P = base.getmatrix(P, (3, None))

        if pose is not None:
            T = self.pose.inv()
        else:
            T = SE3()
        if objpose is not None:
            T *= objpose
        
        R = np.sqrt(np.sum(P ** 2, axis=0))
        phi = np.arctan2(P[1, :], P[0, :])
        theta = np.arccos(P[2, :] / R)
        
        r = self.rfunc(theta)
        x = r * np.cos(phi)
        y = r * np.sin(phi)
        
        uv = np.array([x / self.rhou + self.u0, y / self.rhov + self.v0])
        
        return self.add_noise_distortion(uv)

# ------------------------------------------------------------------------ #

class CatadioptricCamera(Camera):
    """
    Catadioptric camera class

    This camera model assumes central projection, that is, the focal point
    is at z=0 and the image plane is at z=f.  The image is not inverted.

    :seealso: :class:`Camera`
    """

    def __init__(self, k=None, projection='equiangular', maxangle=None, **kwargs):
        r"""
        Catadioptric camera object

        :param k: scale factor
        :type k: float, optional
        :param projection: projection model: ``'equiangular'`` [default], ``'sine'``, ``'equisolid'`` or ``'stereographic'``
        :type projection: str, optional

        The elevation angle range is from :math:`-pi/2` (below the mirror) to
        maxangle above the horizontal plane. The mapping from elevation angle
        :math:`\theta` to image plane radius is given by:

            =============   =======================================
            Projection      :math:`r(\theta)`
            =============   =======================================
            equiangular     :math:`r = k \theta`
            sine            :math:`r = k \sin \theta`
            equisolid       :math:`r = k \sin \frac{\theta}{2}`
            stereographic   :math:`r = k \tan \frac{\theta}{2}`
            =============   =======================================


        .. note:: If K is not specified it is computed such that the circular
          imaging region maximally fills the square image plane.
        
        :seealso: :class:`~machinevisiontoolbox.Camera.Camera` :class:`~machinevisiontoolbox.Camera.CentralCamera`
            :class:`~machinevisiontoolbox.Camera.FisheyeCamera` :class:`~machinevisiontoolbox.Camera.SphericalCamera`
        """

        super().__init__(camtype='catadioptric', **kwargs)

        self.projection = projection
    
        if k is None:
            r = np.min((self.imagesize - self.pp) * self.rho)

        # compute k if not specified, so that hemisphere fits into
        # image plane, requires maxangle being set

        if self.projection == 'equiangular':
            if k is None:
                if maxangle is not None:
                    k = r / (pi / 2 + maxangle)
                    self.maxangle = maxangle
                else:
                    raise ValueError('must specify either k or maxangle')
            rfunc = lambda theta: k * theta
        elif self.projection == 'sine':
            if k is None:
                k = r
            rfunc = lambda theta: k * np.sin(theta)
        elif self.projection == 'equisolid':
            if k is None:
                k = r / sin(pi / 4)
            rfunc = lambda theta: k * np.sin(theta / 2)
        elif self.projection == 'stereographic':
            if k is None:
                k = r / tan(pi/4)
            rfunc = lambda theta: k * np.tan(theta / 2)
        else:
            raise ValueError('unknown projection model')

        self.k = k
        self.rfunc = rfunc

    def __str__(self):
        s = super().__str__()
        s += self.fmt.format('model', self.projection, fmt="{}")
        s += self.fmt.format('k', self.k, fmt="{:.4g}")
        return s

    def project_point(self, P, pose=None, objpose=None):        
        """
        Project 3D points to image plane

        :param P: 3D points to project into camera image plane
        :type P: array_like(3), array_like(3,n)
        :param pose: camera pose with respect to the world frame, defaults to
            camera's ``pose`` attribute
        :type pose: SE3, optional
        :param objpose:  3D point reference frame, defaults to world frame
        :type objpose: SE3, optional
        :param visibility: test if points are visible, default False
        :type visibility: bool
        :raises ValueError: [description]
        :return: image plane points
        :rtype: ndarray(2,n)

        World points are projected to the image plane and represented
        by columns, each column is the u- and v-coordinate.

        If ``pose`` is specified it is used for the camera pose instead of the
        attribute ``pose``.  The object's attribute is not updated.

        The points ``P`` are by default with respect to the world frame, but 
        they can be transformed by specifying ``objpose``.
        """
        P = base.getmatrix(P, (3, None))

        if pose is not None:
            T = self.pose.inv()
        else:
            T = SE3()
        if objpose is not None:
            T *= objpose

        P = T * P  # transform points to camera frame
    
        # project to the image plane
        R = np.sqrt(np.sum(P ** 2, axis=0))
        phi = np.arctan2(P[1, :], P[0, :])
        theta = np.arccos(P[2, :] / R)
        
        r = self.rfunc(theta)  # depends on projection model
        x = r * np.cos(phi)
        y = r * np.sin(phi)
        
        uv = np.array([x / self.rhou + self.u0, y / self.rhov + self.v0])
        
        return self.add_noise_distortion(uv)

# ------------------------------------------------------------------------ #
class SphericalCamera(Camera):
    
        
    def __init__(self, **kwargs):
        #SphericalCamera.Spherical Create spherical projection camera object
        #
        # C = SphericalCamera() creates a spherical projection camera with canonic
        # parameters: f=1 and name='canonic'.
        #
        # C = CentralCamera(OPTIONS) as above but with specified parameters.
        #
        # Options::
        # 'name',N                  Name of camera
        # 'pixel',S                 Pixel size: SxS or S(1)xS(2)
        # 'pose',T                  Pose of the camera as a homogeneous
        #                           transformation
        #
        # See also Camera, CentralCamera, FisheyeCamera, CatadioptricCamera.
        
        # invoke the superclass constructor
        super().__init__(camtype='spherical', 
            limits=[-pi,pi,0,pi],
            labels=['Longitude $\phi$ (rad)', 'Colatitude $\theta$ (rad)'],
            **kwargs)

    # return field-of-view angle for x and y direction (rad)
    def fov(self):
        return [2 * pi, 2 * pi]
    
    def project_point(self, P, pose=None, objpose=None):
        """
        Project 3D points to image plane

        :param P: 3D points to project into camera image plane
        :type P: array_like(3), array_like(3,n)
        :param pose: camera pose with respect to the world frame, defaults to
            camera's ``pose`` attribute
        :type pose: SE3, optional
        :param objpose:  3D point reference frame, defaults to world frame
        :type objpose: SE3, optional
        :return: image plane points
        :rtype: ndarray(2,n)

        World points are projected to the spherical camera image plane and represented
        by columns, each column is $\phi$ (longitude) and $\theta$ (colatitude).

        If ``pose`` is specified it is used for the camera pose instead of the
        attribute ``pose``.  The object's attribute is not updated.

        The points ``P`` are by default with respect to the world frame, but 
        they can be transformed by specifying ``objpose``.
        """
        P = base.getmatrix(P, (3, None))

        if pose is not None:
            T = self.pose.inv()
        else:
            T = SE3()
        if objpose is not None:
            T *= objpose

        P = T * P         # transform points to camera frame
        
        R = np.sqrt( np.sum(P ** 2, axis=0))
        x = P[0, :] / R
        y = P[1, :] / R
        z = P[2, :] / R
        # r = sqrt( x.^2 + y.^2)
        #theta = atan2(r, z)
        theta = np.arccos(P[2, :] / R)
        phi = np.arctan2(y, x)
        return np.array([phi, theta])

if __name__ == "__main__":
    from spatialmath import UnitQuaternion

    cam = CentralCamera()
    P = [0.1, 0.2, 3]
    x = np.r_[cam.pose.t, UnitQuaternion(cam.pose).vec3]
    print(x)
    p, JA, JB = cam.derivatives(x, P)
    print(p)
    print(cam.project_point(P))
    print(JA)
    print(JB)

    # smb.plotvol3(2)

    # cam.plot_camera(scale=0.5, shape='camera', T=SE3.Ry(np.pi/2))

    # plt.show(block=True)
    # print(cam)
    # # cam.pose = SE3([0.1, 0.2, 0.3])
    # print(cam.pose)
    # # fig, ax = c.plot_camera(frustum=True)
    # # plt.show()
    # np.set_printoptions(linewidth=120, formatter={'float': lambda x: f"{x:8.4g}" if abs(x) > 1e-10 else f"{0:8.4g}"})


    # print(cam.project([1,2,3]))

    # print(cam.visjac_p((300,300), 1))
    # cam.flowfield([0,0,0, 0,0,1])
    # # fundamental matrix
    # # create +8 world points (20 in this case)
    # nx, ny = (4, 5)
    # depth = 3
    # x = np.linspace(-1, 1, nx)
    # y = np.linspace(-1, 1, ny)
    # X, Y = np.meshgrid(x, y)
    # Z = depth * np.ones(X.shape)
    # P = np.dstack((X, Y, Z))
    # PC = np.ravel(P, order='C')
    # PW = np.reshape(PC, (3, nx * ny), order='F')

    # # create projections from pose 1:
    # print(c.T)
    # p1 = c.project(PW)  # p1 wrt c's T
    # print(p1)
    # c.plot(PW)

    # # define pose 2:
    # T2 = SE3([0.4, 0.2, 0.3])  # just pure x-translation
    # p2 = c.project(PW, T2)
    # print(p2)
    # c.plot(p2)

    # # convert p1, p2 into lists of points?
    # p1 = np.float32(np.transpose(p1))
    # p2 = np.float32(np.transpose(p2))
    # F = c.FfromPoints(p1,
    #                   p2,
    #                   method='8p',
    #                   ransacThresh=3,
    #                   confidence=0.99,
    #                   maxiters=10)

    # # to check F:
    # p1h = e2h(p1.T)
    # p2h = e2h(p2.T)
    # pfp = [p2h[:, i].T @ F @ p1h[:, i] for i in range(p1h.shape[1])]
    # # [print(pfpi) for pfpi in pfp]
    # for pfpi in pfp:
    #     print(pfpi)
    # # should be all close to zero, which they are!

    # # essential matrix from points:
    # E = c.EfromPoints(p1, p2, c.C)

    # # TODO verify E

    # import code
    # code.interact(local=dict(globals(), **locals()))