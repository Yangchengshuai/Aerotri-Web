////////////////////////////////////////////////////////////////////
// ImageDDS.h
//
// Copyright 2007 cDc@seacave
// Distributed under the Boost Software License, Version 1.0
// (See http://www.boost.org/LICENSE_1_0.txt)

#ifndef __SEACAVE_IMAGEDDS_H__
#define __SEACAVE_IMAGEDDS_H__


// I N C L U D E S /////////////////////////////////////////////////

#include "Image.h"


namespace SEACAVE {

// S T R U C T S ///////////////////////////////////////////////////

class IO_API CImageDDS : public CImage
{
public:
	CImageDDS();
	virtual ~CImageDDS();

	bool		ReadHeader();
	bool		ReadData(void*, PIXELFORMAT, Size nStride, Size lineWidth);
	bool		WriteHeader(PIXELFORMAT, Size width, Size height, BYTE numLevels);
	bool		WriteData(void*, PIXELFORMAT, Size nStride, Size lineWidth);
}; // class CImageDDS
/*----------------------------------------------------------------*/

} // namespace SEACAVE

#endif // __SEACAVE_IMAGEDDS_H__
