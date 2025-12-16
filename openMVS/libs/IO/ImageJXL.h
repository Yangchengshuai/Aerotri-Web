////////////////////////////////////////////////////////////////////
// ImageJXL.h
//
// Copyright 2025 cDc@seacave
// Distributed under the Boost Software License, Version 1.0
// (See http://www.boost.org/LICENSE_1_0.txt)

#ifndef __SEACAVE_IMAGEJXL_H__
#define __SEACAVE_IMAGEJXL_H__


// D E F I N E S ///////////////////////////////////////////////////


// I N C L U D E S /////////////////////////////////////////////////

#include "Image.h"


namespace SEACAVE {

// S T R U C T S ///////////////////////////////////////////////////

class IO_API CImageJXL : public CImage
{
public:
	CImageJXL();
	virtual ~CImageJXL();

	void		Close();

	bool		ReadHeader();
	bool		ReadData(void*, PIXELFORMAT, Size nStride, Size lineWidth);
	bool		WriteHeader(PIXELFORMAT, Size width, Size height, BYTE numLevels);
	bool		WriteData(void*, PIXELFORMAT, Size nStride, Size lineWidth);

protected:
	void*		m_state; // placeholder for JpegXL decoder/encoder state
}; // class CImageJXL
/*----------------------------------------------------------------*/

} // namespace SEACAVE

#endif // __SEACAVE_IMAGEJXL_H__
