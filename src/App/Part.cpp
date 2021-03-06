/***************************************************************************
 *   Copyright (c) J�rgen Riegel          (juergen.riegel@web.de) 2014     *
 *                                                                         *
 *   This file is part of the FreeCAD CAx development system.              *
 *                                                                         *
 *   This library is free software; you can redistribute it and/or         *
 *   modify it under the terms of the GNU Library General Public           *
 *   License as published by the Free Software Foundation; either          *
 *   version 2 of the License, or (at your option) any later version.      *
 *                                                                         *
 *   This library  is distributed in the hope that it will be useful,      *
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
 *   GNU Library General Public License for more details.                  *
 *                                                                         *
 *   You should have received a copy of the GNU Library General Public     *
 *   License along with this library; see the file COPYING.LIB. If not,    *
 *   write to the Free Software Foundation, Inc., 59 Temple Place,         *
 *   Suite 330, Boston, MA  02111-1307, USA                                *
 *                                                                         *
 ***************************************************************************/


#include "PreCompiled.h"

#ifndef _PreComp_
#endif

#include <App/Document.h>
#include <App/Plane.h>

#include "Part.h"
#include "PartPy.h"


using namespace App;


PROPERTY_SOURCE(App::Part, App::GeoFeatureGroup)



//===========================================================================
// Feature
//===========================================================================


const char* Part::BaseplaneTypes[3] = {"XY_Plane", "XZ_Plane", "YZ_Plane"};
const char* Part::BaselineTypes[3] = {"X_Axis", "Y_Axis", "Z_Axis"};

Part::Part(void)
{
    ADD_PROPERTY(Type,(""));
    ADD_PROPERTY_TYPE(Material, (), 0, App::Prop_None, "Map with material properties");
    ADD_PROPERTY_TYPE(Meta, (), 0, App::Prop_None, "Map with additional meta information");

    // create the uuid for the document
    Base::Uuid id;
    ADD_PROPERTY_TYPE(Id, (""), 0, App::Prop_None, "ID (Part-Number) of the Item");
    ADD_PROPERTY_TYPE(Uid, (id), 0, App::Prop_None, "UUID of the Item");

    // license stuff
    ADD_PROPERTY_TYPE(License, ("CC BY 3.0"), 0, App::Prop_None, "License string of the Item");
    ADD_PROPERTY_TYPE(LicenseURL, ("http://creativecommons.org/licenses/by/3.0/"), 0, App::Prop_None, "URL to the license text/contract");
    // color and apperance
    ADD_PROPERTY(Color, (1.0, 1.0, 1.0, 1.0)); // set transparent -> not used

}

Part::~Part(void)
{
}


PyObject *Part::getPyObject()
{
    if (PythonObject.is(Py::_None())){
        // ref counter is set to 1
        PythonObject = Py::Object(new PartPy(this),true);
    }
    return Py::new_reference_to(PythonObject); 
}


// Python feature ---------------------------------------------------------

// Not quit sure yet makeing Part derivable in Python is good Idea!
// JR 2014

//namespace App {
///// @cond DOXERR
//PROPERTY_SOURCE_TEMPLATE(App::PartPython, App::Part)
//template<> const char* App::PartPython::getViewProviderName(void) const {
//    return "Gui::ViewProviderPartPython";
//}
//template<> PyObject* App::PartPython::getPyObject(void) {
//    if (PythonObject.is(Py::_None())) {
//        // ref counter is set to 1
//        PythonObject = Py::Object(new FeaturePythonPyT<App::PartPy>(this),true);
//    }
//    return Py::new_reference_to(PythonObject);
//}
///// @endcond
//
//// explicit template instantiation
//template class AppExport FeaturePythonT<App::Part>;
//}