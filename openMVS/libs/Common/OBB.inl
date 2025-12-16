////////////////////////////////////////////////////////////////////
// OBB.inl
//
// Copyright 2007 cDc@seacave
// Distributed under the Boost Software License, Version 1.0
// (See http://www.boost.org/LICENSE_1_0.txt)


// D E F I N E S ///////////////////////////////////////////////////


// S T R U C T S ///////////////////////////////////////////////////

template <typename TYPE, int DIMS>
inline TOBB<TYPE,DIMS>::TOBB(bool)
	:
	m_rot(MATRIX::Identity()),
	m_pos(POINT::Zero()),
	m_ext(POINT::Zero())
{
}
template <typename TYPE, int DIMS>
inline TOBB<TYPE,DIMS>::TOBB(const AABB& aabb)
{
	Set(aabb);
}
template <typename TYPE, int DIMS>
inline TOBB<TYPE,DIMS>::TOBB(const MATRIX& rot, const POINT& ptMin, const POINT& ptMax)
{
	Set(rot, ptMin, ptMax);
}
template <typename TYPE, int DIMS>
inline TOBB<TYPE,DIMS>::TOBB(const POINT* pts, size_t n)
{
	Set(pts, n);
}
template <typename TYPE, int DIMS>
inline TOBB<TYPE,DIMS>::TOBB(const POINT* pts, size_t n, const TRIANGLE* tris, size_t s)
{
	Set(pts, n, tris, s);
} // constructor
template <typename TYPE, int DIMS>
template <typename CTYPE>
inline TOBB<TYPE,DIMS>::TOBB(const TOBB<CTYPE,DIMS>& rhs)
	:
	m_rot(rhs.m_rot.template cast<TYPE>()),
	m_pos(rhs.m_pos.template cast<TYPE>()),
	m_ext(rhs.m_ext.template cast<TYPE>())
{
} // copy constructor
/*----------------------------------------------------------------*/


template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::Reset()
{
	m_rot.setIdentity();
	m_pos = POINT::Zero();
	m_ext = POINT::Zero();
}
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::Set(const AABB& aabb)
{
	m_rot.setIdentity();
	m_pos = aabb.GetCenter();
	m_ext = aabb.GetSize()/TYPE(2);
}

// build from rotation matrix from world to local, and local min/max corners
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::Set(const MATRIX& rot, const POINT& ptMin, const POINT& ptMax)
{
	m_rot = rot;
	m_pos = (ptMax + ptMin) * TYPE(0.5);
	m_ext = (ptMax - ptMin) * TYPE(0.5);
}

// Inspired from "Fitting Oriented Bounding Boxes" by James Gregson
// http://jamesgregson.blogspot.ro/2011/03/latex-test.html

// Build an OBB from a vector of input points.  This
// method just forms the covariance matrix and hands
// it to the build_from_covariance_matrix method
// which handles fitting the box to the points.
//
// If k (number of nearest neighbors) is set, the method will filter
// out inside points and use only the surface points. This is useful
// when the dominant direction of the inside points is not aligned with
// the convex hull which ultimately is used to define the OBB dimensions.
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::Set(const POINT* pts, size_t n, int k, int fixedAxis)
{
	ASSERT(n >= DIMS);

	std::vector<POINT> surfacePoints;
	if (k > 0) {
		// Filter surface points based on the k nearest neighbors
		surfacePoints = FilterSurfacePoints(pts, n, k);
		pts = surfacePoints.data();
		n = surfacePoints.size();
	}

	// loop over the points to find the mean point
	// location and to build the covariance matrix;
	// note that we only have
	// to build terms for the upper triangular 
	// portion since the matrix is symmetric
	POINT mu(POINT::Zero());
	TYPE cxx=0, cxy=0, cxz=0, cyy=0, cyz=0, czz=0;
	for (size_t i=0; i<n; ++i) {
		const POINT& p = pts[i];
		mu += p;
		cxx += p(0)*p(0); 
		cxy += p(0)*p(1); 
		cxz += p(0)*p(2);
		cyy += p(1)*p(1);
		cyz += p(1)*p(2);
		czz += p(2)*p(2);
	}
	const TYPE invN(TYPE(1)/TYPE(n));
	cxx = (cxx - mu(0)*mu(0)*invN)*invN; 
	cxy = (cxy - mu(0)*mu(1)*invN)*invN; 
	cxz = (cxz - mu(0)*mu(2)*invN)*invN;
	cyy = (cyy - mu(1)*mu(1)*invN)*invN;
	cyz = (cyz - mu(1)*mu(2)*invN)*invN;
	czz = (czz - mu(2)*mu(2)*invN)*invN;

	// now build the covariance matrix
	MATRIX C;
	C(0,0) = cxx; C(0,1) = cxy; C(0,2) = cxz;
	C(1,0) = cxy; C(1,1) = cyy; C(1,2) = cyz;
	C(2,0) = cxz; C(2,1) = cyz; C(2,2) = czz;

	// set the OBB parameters from the covariance matrix
	Set(C, pts, n, fixedAxis);
}
// builds an OBB from triangles specified as an array of
// points with integer indices into the point array. Forms
// the covariance matrix for the triangles, then uses the
// method build_from_covariance_matrix method to fit 
// the box.  ALL points will be fit in the box, regardless
// of whether they are indexed by a triangle or not.
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::Set(const POINT* pts, size_t n, const TRIANGLE* tris, size_t s)
{
	ASSERT(n >= DIMS);

	// loop over the triangles this time to find the
	// mean location
	POINT mu(POINT::Zero());
	TYPE Am=0;
	TYPE cxx=0, cxy=0, cxz=0, cyy=0, cyz=0, czz=0;
	for (size_t i=0; i<s; ++i) {
		ASSERT(tris[i](0)<n && tris[i](1)<n && tris[i](2)<n);
		const POINT& p = pts[tris[i](0)];
		const POINT& q = pts[tris[i](1)];
		const POINT& r = pts[tris[i](2)];
		const POINT mui = (p+q+r)/TYPE(3);
		const TYPE Ai = (q-p).cross(r-p).normalize()/TYPE(2);
		mu += mui*Ai;
		Am += Ai;

		// these bits set the c terms to Am*E[xx], Am*E[xy], Am*E[xz]....
		const TYPE Ai12 = Ai/TYPE(12);
		cxx += (TYPE(9)*mui(0)*mui(0) + p(0)*p(0) + q(0)*q(0) + r(0)*r(0))*Ai12;
		cxy += (TYPE(9)*mui(0)*mui(1) + p(0)*p(1) + q(0)*q(1) + r(0)*r(1))*Ai12;
		cxz += (TYPE(9)*mui(0)*mui(2) + p(0)*p(2) + q(0)*q(2) + r(0)*r(2))*Ai12;
		cyy += (TYPE(9)*mui(1)*mui(1) + p(1)*p(1) + q(1)*q(1) + r(1)*r(1))*Ai12;
		cyz += (TYPE(9)*mui(1)*mui(2) + p(1)*p(2) + q(1)*q(2) + r(1)*r(2))*Ai12;
		czz += (TYPE(9)*mui(2)*mui(2) + p(2)*p(2) + q(2)*q(2) + r(2)*r(2))*Ai12;
	}

	// divide out the Am fraction from the average position and 
	// covariance terms
	mu /= Am;
	cxx /= Am; cxy /= Am; cxz /= Am; cyy /= Am; cyz /= Am; czz /= Am;

	// now subtract off the E[x]*E[x], E[x]*E[y], ... terms
	cxx -= mu(0)*mu(0); cxy -= mu(0)*mu(1); cxz -= mu(0)*mu(2);
	cyy -= mu(1)*mu(1); cyz -= mu(1)*mu(2); czz -= mu(2)*mu(2);

	// now build the covariance matrix
	MATRIX C;
	C(0,0)=cxx; C(0,1)=cxy; C(0,2)=cxz;
	C(1,0)=cxy; C(1,1)=cyy; C(1,2)=cyz;
	C(2,0)=cxz; C(1,2)=cyz; C(2,2)=czz;

	// set the obb parameters from the covariance matrix
	Set(C, pts, n);
}
// method to set the OBB parameters which produce a box oriented according to
// the covariance matrix C, and that contains the given points
// if fixedAxis is specified (only for 3D OBBs), the OBB rotation be applied in the plane perpendicular
// to the given axis (0=x,1=y,2=z)
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::Set(const MATRIX& C, const POINT* pts, size_t n, int fixedAxis)
{
	// extract rotation from the covariance matrix
	if (fixedAxis >= 0)
		SetRotation(C, fixedAxis);
	else
		SetRotation(C);
	// extract size and center from the given points
	SetBounds(pts, n);
}
// method to set the OBB rotation which produce a box oriented according to
// the covariance matrix C (only the rotations is set)
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::SetRotation(const MATRIX& C)
{
	// extract the eigenvalues and eigenvectors from C
	const Eigen::SelfAdjointEigenSolver<MATRIX> es(C);
	ASSERT(es.info() == Eigen::Success);
	// find the right, up and forward vectors from the eigenvectors
	// and set the rotation matrix using the eigenvectors
	ASSERT(es.eigenvalues()(0) < es.eigenvalues()(1) && es.eigenvalues()(1) < es.eigenvalues()(2));
	m_rot = es.eigenvectors().transpose();
	if (m_rot.determinant() < 0)
		m_rot = -m_rot;
}
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::SetRotation(const MATRIX& C, int fixedAxis)
{
	ASSERT(DIMS == 3); // SetRotation with fixed axis is only implemented for 3D OBBs
	ASSERT(fixedAxis == 0 || fixedAxis == 1 || fixedAxis == 2);
	// the two free axes (wrap-around)
	const int a = (fixedAxis + 1) % 3;
	const int b = (fixedAxis + 2) % 3;
	// 2×2 covariance submatrix for (a,b)
	Eigen::Matrix<TYPE,2,2> C2;
	C2(0,0) = C(a,a);
	C2(0,1) = C(a,b);
	C2(1,0) = C(b,a);
	C2(1,1) = C(b,b);
	Eigen::SelfAdjointEigenSolver<Eigen::Matrix<TYPE,2,2>> es2(C2);
	ASSERT(es2.info() == Eigen::Success);
	// Columns: eigenvectors for ascending eigenvalues (minor -> major)
	const Eigen::Matrix<TYPE,2,1> v0 = es2.eigenvectors().col(0);
	const Eigen::Matrix<TYPE,2,1> v1 = es2.eigenvectors().col(1);
	// Build rotation rows (rows = axes)
	m_rot.setZero();
	// Fixed axis aligns with world basis
	m_rot.row(fixedAxis).setZero();
	m_rot(fixedAxis, fixedAxis) = TYPE(1);
	// In-plane minor direction goes to row 'a'
	m_rot.row(a).setZero();
	m_rot(a, a) = v0(0);
	m_rot(a, b) = v0(1);
	// In-plane major direction goes to row 'b'
	m_rot.row(b).setZero();
	m_rot(b, a) = v1(0);
	m_rot(b, b) = v1(1);
	// Make right-handed: flip the minor row if needed
	if (m_rot.determinant() < TYPE(0))
		m_rot.row(a) = -m_rot.row(a);
}
// method to set the OBB center and size that contains the given points
// the rotations should be already set
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::SetBounds(const POINT* pts, size_t n)
{
	ASSERT(n >= DIMS);
	ASSERT(ISEQUAL((m_rot*m_rot.transpose()).trace(), TYPE(3)) && ISEQUAL(m_rot.determinant(), TYPE(1)));

	// build the bounding box extents in the rotated frame
	AABB aabb(m_rot * pts[0]);
	for (size_t i=1; i<n; ++i)
		aabb.Insert(m_rot * pts[i]);

	// set the center of the OBB to be the average of the 
	// minimum and maximum, and the extents be half of the
	// difference between the minimum and maximum
	m_pos = m_rot.transpose() * aabb.GetCenter();
	m_ext = aabb.GetSize() * TYPE(0.5);
} // Set
/*----------------------------------------------------------------*/


template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::BuildBegin()
{
	m_rot = MATRIX::Zero();
	m_pos = POINT::Zero();
	m_ext = POINT::Zero();
}
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::BuildAdd(const POINT& p)
{
	// store mean in m_pos
	m_pos += p;
	// store covariance params in m_rot
	m_rot(0,0) += p(0)*p(0); 
	m_rot(0,1) += p(0)*p(1); 
	m_rot(0,2) += p(0)*p(2);
	m_rot(1,0) += p(1)*p(1);
	m_rot(1,1) += p(1)*p(2);
	m_rot(1,2) += p(2)*p(2);
	// store count in m_ext
	++(*((size_t*)m_ext.data()));
}
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::BuildEnd()
{
	const TYPE invN(TYPE(1)/TYPE(*((size_t*)m_ext.data())));
	const TYPE cxx = (m_rot(0,0) - m_pos(0)*m_pos(0)*invN)*invN; 
	const TYPE cxy = (m_rot(0,1) - m_pos(0)*m_pos(1)*invN)*invN; 
	const TYPE cxz = (m_rot(0,2) - m_pos(0)*m_pos(2)*invN)*invN;
	const TYPE cyy = (m_rot(1,0) - m_pos(1)*m_pos(1)*invN)*invN;
	const TYPE cyz = (m_rot(1,1) - m_pos(1)*m_pos(2)*invN)*invN;
	const TYPE czz = (m_rot(1,2) - m_pos(2)*m_pos(2)*invN)*invN;

	// now build the covariance matrix
	MATRIX C;
	C(0,0) = cxx; C(0,1) = cxy; C(0,2) = cxz;
	C(1,0) = cxy; C(1,1) = cyy; C(1,2) = cyz;
	C(2,0) = cxz; C(2,1) = cyz; C(2,2) = czz;
	SetRotation(C);
} // Build
/*----------------------------------------------------------------*/


// check if the oriented bounding box has positive size
template <typename TYPE, int DIMS>
inline bool TOBB<TYPE,DIMS>::IsValid() const
{
	return m_ext.minCoeff() > TYPE(0);
} // IsValid
/*----------------------------------------------------------------*/


template <typename TYPE, int DIMS>
inline TOBB<TYPE,DIMS>& TOBB<TYPE,DIMS>::Enlarge(TYPE x)
{
	m_ext.array() += x;
	return *this;
}
template <typename TYPE, int DIMS>
inline TOBB<TYPE,DIMS>& TOBB<TYPE,DIMS>::EnlargePercent(TYPE x)
{
	m_ext *= x;
	return *this;
} // Enlarge
/*----------------------------------------------------------------*/


// Update the box by the given pos delta.
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::Translate(const POINT& d)
{
	m_pos += d;
}
// Update the box by the given transform.
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::Transform(const MATRIX& m)
{
	Eigen::Transform<Type, DIMS, Eigen::Affine> transform(m);
	MATRIX rotation, scaling;
	transform.computeRotationScaling(&rotation, &scaling);
	m_rot = rotation * m_rot;
	m_pos = m * m_pos;
	m_ext = scaling * m_ext;
} // Transform
/*----------------------------------------------------------------*/


template <typename TYPE, int DIMS>
inline typename TOBB<TYPE,DIMS>::POINT TOBB<TYPE,DIMS>::GetCenter() const
{
	return m_pos;
}
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::GetCenter(POINT& ptCenter) const
{
	ptCenter = m_pos;
} // GetCenter
/*----------------------------------------------------------------*/


template <typename TYPE, int DIMS>
inline typename TOBB<TYPE,DIMS>::POINT TOBB<TYPE,DIMS>::GetSize() const
{
	return m_ext*2;
}
template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::GetSize(POINT& ptSize) const
{
	ptSize = m_ext*2;
} // GetSize
/*----------------------------------------------------------------*/


template <typename TYPE, int DIMS>
inline void TOBB<TYPE,DIMS>::GetCorners(POINT pts[numCorners]) const
{
	// generate all corner combinations using bit patterns;
	// use bit j of i to determine sign: 0 = subtract, 1 = add
	POINT axisVectors[DIMS];
	for (int j=0; j<DIMS; ++j)
		axisVectors[j] = m_rot.row(j) * m_ext[j];
	for (int i=0; i<numCorners; ++i) {
		pts[i] = m_pos;
		for (int j=0; j<DIMS; ++j) {
			if (i & (1 << j))
				pts[i] += axisVectors[j];
			else
				pts[i] -= axisVectors[j];
		}
	}
} // GetCorners
// constructs the corner of the aligned bounding box in world space
template <typename TYPE, int DIMS>
inline typename TOBB<TYPE,DIMS>::AABB TOBB<TYPE,DIMS>::GetAABB() const
{
	POINT pts[numCorners];
	GetCorners(pts);
	return AABB(pts, numCorners);
} // GetAABB
/*----------------------------------------------------------------*/

// computes the volume of the OBB, which is a measure of
// how tight the fit is (better OBBs will have smaller volumes)
template <typename TYPE, int DIMS>
inline TYPE TOBB<TYPE,DIMS>::GetVolume() const
{
	return m_ext.prod()*numCorners;
}
/*----------------------------------------------------------------*/


template <typename TYPE, int DIMS>
bool TOBB<TYPE,DIMS>::Intersects(const POINT& pt) const
{
	const POINT dist(m_rot * (pt - m_pos));
	return (dist.array().abs() <= m_ext.array()).all();
} // Intersects(POINT)
/*----------------------------------------------------------------*/


// Surface (aproximate) point extraction from 3D point clouds using directional vector summation.
//
// This algorithm approximates which points lie on the surface (outer boundary) of a 3D point cloud,
// based on the spatial distribution of their neighbors.
//
// For each point:
// 1. Find its k nearest neighbors using a KD-tree (via nanoflann).
// 2. Compute unit direction vectors from the point to each neighbor.
// 3. Sum all direction vectors and compute the magnitude of the result.
//    - A large magnitude indicates an asymmetric neighborhood — likely a surface point.
//    - A near-zero magnitude indicates a symmetric (interior) neighborhood.
//
// After computing this "surface score" for each point, the algorithm selects the top N% of points
// with the highest scores as likely surface points.

template <typename TYPE, int DIMS>
struct TPointCloudSurfaceAdaptor {
	const typename TOBB<TYPE,DIMS>::POINT* pts;
	size_t n;
	TPointCloudSurfaceAdaptor(const typename TOBB<TYPE,DIMS>::POINT* pts_, size_t n_) : pts(pts_), n(n_) {}
	inline size_t kdtree_get_point_count() const { return n; }
	inline TYPE kdtree_get_pt(const size_t idx, int dim) const { return pts[idx][dim]; }
	template <class BBOX>
	bool kdtree_get_bbox(BBOX&) const { return false; }
};

template <typename TYPE, int DIMS>
std::vector<TYPE> TOBB<TYPE,DIMS>::ComputeSurfacePointsScores(const POINT* pts, size_t n, int k)
{
	using PointCloudSurfaceAdaptor = TPointCloudSurfaceAdaptor<TYPE, DIMS>;
	using KDTree = nanoflann::KDTreeSingleIndexAdaptor<
		nanoflann::L2_Simple_Adaptor<TYPE, PointCloudSurfaceAdaptor>,
		PointCloudSurfaceAdaptor, DIMS>;

	PointCloudSurfaceAdaptor adaptor(pts, n);
	KDTree kdtree(DIMS, adaptor, nanoflann::KDTreeSingleIndexAdaptorParams());
	kdtree.buildIndex();

	std::vector<TYPE> scores(n);
	std::vector<size_t> indices(k + 1);
	std::vector<TYPE> dists(k + 1);
	for (size_t i = 0; i < n; ++i) {
		nanoflann::KNNResultSet<TYPE> resultSet(k + 1);
		resultSet.init(indices.data(), dists.data());
		kdtree.findNeighbors(resultSet, &pts[i][0], nanoflann::SearchParameters());
		POINT sum_vector = POINT::Zero();
		for (size_t j = 1; j < resultSet.size(); ++j) { // skip self
			POINT dir = pts[indices[j]] - pts[i];
			TYPE norm = dir.norm();
			if (!ISZERO(norm))
				sum_vector += dir / norm;
		}
		scores[i] = sum_vector.norm();
	}
	return scores;
}

template <typename TYPE, int DIMS>
std::vector<typename TOBB<TYPE,DIMS>::POINT> TOBB<TYPE,DIMS>::FilterSurfacePoints(const POINT* pts, size_t n, int k, TYPE percentile)
{
	auto scores = ComputeSurfacePointsScores(pts, n, k);
	TYPE threshold;
	if (percentile > 0) {
		// Calculate the index for the given percentile
		size_t index = static_cast<size_t>((TYPE(1) - percentile) * scores.size());
		const auto nth = scores.begin() + index;
		std::nth_element(scores.begin(), nth, scores.end());
		threshold = *nth;
	} else {
		// Use given percentile param as threshold
		threshold = -percentile;
	}
	std::vector<POINT> result;
	for (size_t i = 0; i < n; ++i) {
		if (scores[i] > threshold)
			result.push_back(pts[i]);
	}
	return result;
}
/*----------------------------------------------------------------*/
