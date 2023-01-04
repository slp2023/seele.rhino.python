import sys
import System
import json
import copy
import math
import os
import copy 

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

#globalpath=r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\seele.Rhino.Common"
#sys.path.append(globalpath)

import seeleScriptSyntax as ss
see = ss.seeleScriptSyntax()


crv = rs.GetObject("crv",rs.filter.curve)

trimsrf1 = rs.GetObject("srf1",rs.filter.surface)
trimsrf2 = rs.GetObject("srf2",rs.filter.surface)

newcrv = see.TrimCurve(crv, Rhino.Geometry.CurveEnd.Both, 10, trimsrf1, trimsrf2)
#print newcrv

#sc.doc.Objects.Add(newcrv)





 
