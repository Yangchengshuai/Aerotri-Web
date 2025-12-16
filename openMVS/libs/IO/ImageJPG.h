////////////////////////////////////////////////////////////////////
// ImageJPG.h
//
// Copyright 2007 cDc@seacave
// Distributed under the Boost Software License, Version 1.0
// (See http://www.boost.org/LICENSE_1_0.txt)

#ifndef __SEACAVE_IMAGEJPG_H__
#define __SEACAVE_IMAGEJPG_H__


// D E F I N E S ///////////////////////////////////////////////////


// I N C L U D E S /////////////////////////////////////////////////

#include "Image.h"


namespace SEACAVE {

// S T R U C T S ///////////////////////////////////////////////////

class IO_API CImageJPG : public CImage
{
public:
	CImageJPG();
	virtual ~CImageJPG();

	void		Close();

	bool		ReadHeader();
	bool		ReadData(void*, PIXELFORMAT, Size nStride, Size lineWidth);
	bool		WriteHeader(PIXELFORMAT, Size width, Size height, BYTE numLevels);
	bool		WriteData(void*, PIXELFORMAT, Size nStride, Size lineWidth);

protected:
	void*		m_state;
}; // class CImageJPG
/*----------------------------------------------------------------*/

} // namespace SEACAVE

#endif // __SEACAVE_IMAGEJPG_H__
