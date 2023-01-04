# -*- encoding: utf-8 -*-
"""
Script created by M.Huber for Seele GmbH
Copyright by Seele GmbH

Comments:
# 2022-05-02 Update mhu::     initialized
#
#

Description:
# A collection of RhinoScript-like functions that can be called from Python
"""

import sys
import json
import System
import math
import os
import copy 

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

tolmod = sc.doc.ModelAbsoluteTolerance

class seeleScriptSyntax():
    
    def __init__(self):
        self.Name="seeleScriptSyntax"
        
    ### list collection:
    def SortObjects(self,objects,sortmeth,testpt=None,reverse=False,coerce_out=False):
        
        """Sorts objects("objs") according to a defined method ("sortmeth")
        Parameters:
          object ([guid or geo representation, ...]) : identifiers of objects (surfaces, curves)
          sortmeth :  surfaces    "area_srf" / "X/Y/Z_srf" / "dis_area"
                      curves      "len_crv"  / "X/Y/Z_crv"
                      breps       "vol_brep" / "X/Y/Z_brep"
                      testpt      "dis_point"
        Returns:
          list(guid) : sorted list ([[key,value],...]) 
        
        Example:
          sorted_list = see.SortObjects(objs,sortmeth,reverse=True):
        
        """
        
        sortval = sortmeth.split("_")[0]
        objtype = sortmeth.split("_")[1]
        
        ### translate GUID to brep/curve representation
        obj_list = []
        for obj in objects:
            if obj!=System.Guid:
                if objtype=="srf" or objtype=="brep":
                    obj_list.append(rs.coercebrep(obj))
                elif objtype=="crv":
                    obj_list.append(rs.coercecurve(obj))
        if coerce_objs==[]:
            obj_list = objects
        
        ### check if valid object
        val_objs = []
        index_invalid = []
        for i,objx in enumerate(obj_list):
            if objx.IsValid:
                allvalid = True
                val_objs.append(objx)
            else:
                allvalid = False
                index_invalid.append(i)
        
        ### init sort process
        if objtype=="srf":
            if sortval=="area":
                a_objs = []
                for obj in val_objs:
                    a_objs.append([Rhino.Geometry.AreaMassProperties.Compute(obj).Area,obj])
                
                sortobjs = sorted(a_objs, key=lambda a:a[0], reverse=reverse)
                
            elif sortval=="X" or sortval=="Y" or sortval=="Z":
                xyz_objs = []
                for obj in val_objs:
                    if sortval=="X":
                        xyz_objs.append([Rhino.Geometry.AreaMassProperties.Compute(obj).Centroid.X,obj])
                    elif sortval=="Y":
                        xyz_objs.append([Rhino.Geometry.AreaMassProperties.Compute(obj).Centroid.Y,obj])
                    else:
                        xyz_objs.append([Rhino.Geometry.AreaMassProperties.Compute(obj).Centroid.Z,obj])
                sortobjs = sorted(xyz_objs, key=lambda xyz:xyz[0], reverse=reverse)
            
            elif sortval=="dis":
                dis_srf = []
                for obj in val_objs:
                    dis = testpt.DistanceTo(Rhino.Geometry.AreaMassProperties.Compute(obj).Centroid)
                    dis_srf.append([dis,obj])
                sortobjs = sorted(dis_srf,key=lambda dis:dis[0], reverse=reverse)
                
        elif objtype=="crv":
            if sortval=="len":
                l_objs = []
                for obj in val_objs:
                    l_objs.append([obj.GetLength(),obj])
                sortobjs = sorted(l_objs, key=lambda l:l[0], reverse=reverse)
                
            elif sortval=="X" or sortval=="Y" or sortval=="Z":
                xyz_objs = []
                for obj in val_objs:
                    if sortval=="X":
                        obj.PointAt(obj.NormalizedLengthParameter(0.5)[1])
                        xyz_objs.append([obj.PointAt(obj.NormalizedLengthParameter(0.5)[1]).X,obj])
                    elif sortval=="Y":
                        xyz_objs.append([obj.PointAt(obj.NormalizedLengthParameter(0.5)[1]).Y,obj])
                    else:
                        xyz_objs.append([obj.PointAt(obj.NormalizedLengthParameter(0.5)[1]).Z,obj])
                sortobjs = sorted(xyz_objs, key=lambda xyz:xyz[0], reverse=reverse)
            
            elif sortval=="dis":
                dis_crv = []
                for obj in val_objs:
                    dis = testpt.DistanceTo(obj.PointAt(obj.NormalizedLengthParameter(0.5)[1]))
                    dis_crv.append([dis,obj])
                sortobjs = sorted(dis_crv,key=lambda dis:dis[0], reverse=reverse)
        
        elif objtype=="point":
            if sortval=="dis":
                dis_pt = []
                for obj in val_objs:
                    dis = testpt.DistanceTo(obj)
                    dis_pt.append([dis,obj])
                sortobjs = sorted(dis_pt,key=lambda dis:dis[0], reverse=reverse)
        
        ### translate representation to GUID
        if coerce_out:
            res = []
            for sobj in sortobjs:
                res.append([sobj,sc.doc.Objects.Add(sobj[1])])
        else:
            res = sortobjs
        
        ### print message if object not valid
        if len(index_invalid)>1:
            for index in index_invalid:
                print "object with index " + str(index) + " is invalid"
                
        return res
    
    ### intersection collection:
    def SplitBrepCutters(self,brep,cutter_objs,coerce=True):
        
        """Splits a brep with multiple cutters
        Parameters:
          brep (guid): identifier of the brep to split
          cutter_objs ([guid, ...]): identifier of the breps to split with
        Returns:
          list(guid, ...): identifiers of split pieces on success
          None: on error
        Example:
          import rhinoscriptsyntax as rs
          filter = rs.filter.surface + rs.filter.polysurface
          brep = rs.GetObject("Select brep to split", filter)
          cutter = rs.GetObject("Select cutting brep", filter)
          rs.SplitBrep ( brep, cutter )
        See Also:
          IsBrep
        """
        
        cutobjs = Rhino.Geometry.Brep()
        
        if coerce==True:
            coebrep = rs.coercebrep(brep)
            for cc in cutter_objs:
                cutobjs.Append(rs.coercebrep(cc))
        else:
            coebrep = brep
            for cc in cutter_objs:
                cutobjs.Append(cc)
        
        res = coebrep.Split(cutobjs, 0.001)
        
        if not res: return sc.errorhandler()
        else:
            checked_res=[] 
            for r in res:
                if r.IsValid:
                    checked_res.append(r)
            return checked_res
    
    def TrimCurve(self,crv,extside,extval,trimsrf1,trimsrf2):
        
        see = seeleScriptSyntax()
        
        if crv!=System.Guid:
            crv = rs.coercecurve(crv)
        if trimsrf1!=System.Guid:
            trimsrf1 = rs.coercebrep(trimsrf1)
        if trimsrf2!=System.Guid:
            trimsrf2 = rs.coercebrep(trimsrf2)
        
        crv_ext = crv.Extend(extside, extval, Rhino.Geometry.CurveExtensionStyle.Smooth)
        crv_add = sc.doc.Objects.Add(crv_ext)
        
        # CurveBrep akzeptiert nur "Curve"-Objekt, noch keinen Weg zur Umwandlung gefunden
        #crv_split = crv.Split([crv.CurveBrep(trimsrf1,tolmod).ParameterA, crv.CurveBrep(trimsrf2,tolmod).ParameterA])
        
        crv_split = rs.SplitCurve(crv_add,
            [rs.CurveClosestPoint(crv_add,rs.CurveBrepIntersect(crv_add,trimsrf1)[1][0]),
            rs.CurveClosestPoint(crv_add,rs.CurveBrepIntersect(crv_add,trimsrf2)[1][0])])
        
        crv_sort = see.SortObjects(crv_split,sortmeth="len_crv",testpt=None,reverse=True,coerce_in=True,coerce_out=False)
        crv_res = crv_sort[0][1]
        
        return crv_res
    
seeleScriptSyntax()