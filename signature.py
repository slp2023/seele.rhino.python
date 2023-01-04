# -*- encoding: utf-8 -*-
"""
Script written by S. Lippert for Seele GmbH
Version 2.0 as of 2018-05-03
Copyright by Seele GmbH

2020-02-26 Update slp::     Added Text3D class - simplified text brep factory for signature engraving on solids - 
                            due to instability of Rhino.Geometry.TextEntity().CreatePolySurfaces()
"""

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import os.path as osp
import clr
clr.AddReference("System.Xml.Linq")
from System.Xml.Linq import * #die einzig funktionale xml implementierung

class EasyType:
    
    """
    written by slp as of 2017-11-24
    class transforms rhino text to TRUMPF readable punch marks
    useful for sheetmetal dxf export
    """
    def __init__(self,path=r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\lib",spacing=2):
        
        self.Chars="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-+"
        self.Path=path
        self.File="easytype_2D.xml"
        self.Letters={}
        self.Spacing=spacing
        self.Size={}
        
        if osp.exists(self.Path+"\\"+self.File):
            self.__GeoFromXML()
            
    def GeoToXML(self,path=r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\lib"):
        
        rs.EnableRedraw(False)
        xmlRoot=XElement("easytype_chars")
        
        for x in self.Chars:
            #rs.Command("-_import " +  path+"\\" + x+".3dm _enter")
            polycurves=rs.ObjectsByLayer(x)
            #polycurves=rs.LastCreatedObjects()
            bbx=rs.BoundingBox(polycurves)
            sizex=bbx[0].DistanceTo(bbx[1])
            sizey=bbx[0].DistanceTo(bbx[3])
            
            if x=="+":
                xmlLetter=XElement("char_PLUS")
            elif x=="-":
                xmlLetter=XElement("char_MINUS")
            else:
                xmlLetter=XElement("char_"+x)
            xmlRoot.Add(xmlLetter)
            xmlLetter.Add(XAttribute("dX",str(sizex)))
            xmlLetter.Add(XAttribute("dY",str(sizey)))
            
            for i in range(0,len(polycurves)):
                curve=rs.coercegeometry(polycurves[i])
                #rc, polyline = curve.TryGetPolyline()
                xmlPolyCurve=XElement("polycurve_"+str(i))
                xmlLetter.Add(xmlPolyCurve)
                curves=curve.Explode()
                for j in range(0,len(curves)):
                    #curves[j].TryGetLine()
                    if isinstance(curves[j],Rhino.Geometry.LineCurve):
                        xmlCurveSegment=XElement("line_"+str(j))
                        pts=[curves[j].Line.From,curves[j].Line.To]
                    elif isinstance(curves[j],Rhino.Geometry.ArcCurve):
                        xmlCurveSegment=XElement("arc_"+str(j))
                        pts=[curves[j].Arc.StartPoint,curves[j].Arc.MidPoint,curves[j].Arc.EndPoint]
                    else:
                        break
                    xmlPolyCurve.Add(xmlCurveSegment)
                    k=0
                    for pt in pts:
                        xmlPoint=XElement("point_"+str(k))
                        xmlCurveSegment.Add(xmlPoint)
                        xmlPoint.Add(XAttribute("X",str(pt.X)))
                        xmlPoint.Add(XAttribute("Y",str(pt.Y)))
                        xmlPoint.Add(XAttribute("Z",str(pt.Z)))
                        k+=1
            rs.DeleteObjects(polycurves)
            
        xdoc=XDocument(xmlRoot)
        xdoc.Save(self.Path+"\\"+self.File)
        rs.EnableRedraw(True)
        
        return True
    
    def __GeoFromXML(self):
        
        xdoc=XDocument.Load(self.Path+"\\"+self.File)
        xmlRoot=xdoc.Root
        for xele in xmlRoot.Elements():
            char=xele.Name.ToString().replace("char_","")
            if char=="PLUS":
                char="+"
            elif char=="MINUS":
                char="-"
            curves=[]
            for xele1 in xele.Elements():
                polycurve=Rhino.Geometry.PolyCurve()
                for xele2 in xele1.Elements():
                    points=[]
                    for xele3 in xele2.Elements():
                        points.append(Rhino.Geometry.Point3d(float(xele3.Attribute("X").Value),float(xele3.Attribute("Y").Value),float(xele3.Attribute("Z").Value)))
                    if "line" in xele2.Name.ToString():
                        polycurve.Append(Rhino.Geometry.LineCurve(Rhino.Geometry.Line(points[0],points[1])))
                    elif "arc" in xele2.Name.ToString():
                        #rs.AddArc3Pt(points[0],points[1],points[2])    
                        polycurve.Append(Rhino.Geometry.ArcCurve(Rhino.Geometry.Arc(points[0],points[1],points[2])))
                curves.append(polycurve)
            self.Letters[char]=curves
            self.Size[char]=float(xele.Attribute("dX").Value)
            
        return 
                    
    def ConvertText(self,text):
        
        obj=[]
        #cplane stuff
        if rs.IsText(text):
            txtobj=rs.coercegeometry(text)
            cplane=txtobj.Plane
            wplane=Rhino.Geometry.Plane.WorldXY
            txt=txtobj.Text.upper()
            
            ip=cplane.Origin 
            for i in range(0,len(txt)):
                if txt[i]in self.Letters:
                    for j in self.Letters[txt[i]]:
                        cplane.Origin=ip
                        xform=Rhino.Geometry.Transform.ChangeBasis(cplane,wplane)
                        pc=j.Duplicate()
                        pc.Transform(xform)
                        obj.append(sc.doc.Objects.AddCurve(pc))
                    ip+=cplane.XAxis*(self.Size[txt[i]]+self.Spacing)
                elif txt[i]==" ":
                    ip+=cplane.XAxis*self.Spacing*2
                elif txt[i]=="," or txt[i]=="." :
                    ip+=cplane.XAxis*self.Spacing
        else:
            return None
        
        return obj

class Text3D:
    
    """
    written by slp as of 2020-02-25
    class transforms rhino text to solid breps for boolean operations
    useful for solid engraving
    """

    def __init__(self,path=r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\seele.Rhino.Common",spacing=2):
        
        self.Chars="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-+.*#/>"
        self.Path=path
        self.File="easytype_3D.xml"
        self.Letters={}
        self.Spacing=spacing
        self.SizeX={}
        self.SizeY={}
        
        if osp.exists(self.Path+"\\"+self.File):
            self.__GeoFromXML()
            
    def GeoToXML(self,path=r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\lib"):
        
        rs.EnableRedraw(False)
        xmlRoot=XElement("easytype_chars")
        
        for x in self.Chars:
            polycurves=rs.ObjectsByLayer(x)
            bbx=rs.BoundingBox(polycurves)
            sizex=bbx[0].DistanceTo(bbx[1])
            sizey=bbx[0].DistanceTo(bbx[3])
            
            if x=="+":
                xmlLetter=XElement("char_PLUS")
            elif x=="-":
                xmlLetter=XElement("char_MINUS")
            elif x=="/":
                xmlLetter=XElement("char_FSLASH")
            elif x==".":
                xmlLetter=XElement("char_DOT")
            elif x=="#":
                xmlLetter=XElement("char_HASH")
            elif x=="*":
                xmlLetter=XElement("char_STAR")
            elif x==">":
                xmlLetter=XElement("char_ARROWR")
            else:
                xmlLetter=XElement("char_"+x)
            xmlRoot.Add(xmlLetter)
            xmlLetter.Add(XAttribute("dX",str(sizex)))
            xmlLetter.Add(XAttribute("dY",str(sizey)))
            
            for i in range(0,len(polycurves)):
                xmlPolyCurve=XElement("polycurve_"+str(i))
                xmlLetter.Add(xmlPolyCurve)
                curves=[rs.coercegeometry(x) for x in rs.ExplodeCurves(polycurves[i])]
                
                for j in range(0,len(curves)):
                    #curves[j].TryGetLine()
                    if isinstance(curves[j],Rhino.Geometry.LineCurve):
                        xmlCurveSegment=XElement("line_"+str(j))
                        pts=[curves[j].Line.From,curves[j].Line.To]
                    elif isinstance(curves[j],Rhino.Geometry.ArcCurve):
                        xmlCurveSegment=XElement("arc_"+str(j))
                        pts=[curves[j].Arc.StartPoint,curves[j].Arc.MidPoint,curves[j].Arc.EndPoint]
                    else:
                        continue
                    xmlPolyCurve.Add(xmlCurveSegment)
                    k=0
                    for pt in pts:
                        xmlPoint=XElement("point_"+str(k))
                        xmlCurveSegment.Add(xmlPoint)
                        xmlPoint.Add(XAttribute("X",str(pt.X)))
                        xmlPoint.Add(XAttribute("Y",str(pt.Y)))
                        xmlPoint.Add(XAttribute("Z",str(pt.Z)))
                        k+=1
            #rs.DeleteObjects(polycurves)
            
        xdoc=XDocument(xmlRoot)
        xdoc.Save(self.Path+"\\"+self.File)
        rs.EnableRedraw(True)
        
        return True

    def __GeoFromXML(self):
        
        xdoc=XDocument.Load(self.Path+"\\"+self.File)
        xmlRoot=xdoc.Root
        for xele in xmlRoot.Elements():
            char=xele.Name.ToString().replace("char_","")
            if char=="PLUS":
                char="+"
            elif char=="MINUS":
                char="-"
            elif char=="FSLASH":
                char="/"
            elif char=="DOT":
                char="."
            elif char=="HASH":
                char="#"
            elif char=="STAR":
                char="*"
            elif char=="ARROWR":
                char=">"

            curves=[]
            for xele1 in xele.Elements():
                polycurve=Rhino.Geometry.PolyCurve()
                for xele2 in xele1.Elements():
                    points=[]
                    for xele3 in xele2.Elements():
                        points.append(Rhino.Geometry.Point3d(float(xele3.Attribute("X").Value),float(xele3.Attribute("Y").Value),float(xele3.Attribute("Z").Value)))
                    if "line" in xele2.Name.ToString():
                        polycurve.Append(Rhino.Geometry.LineCurve(Rhino.Geometry.Line(points[0],points[1])))
                    elif "arc" in xele2.Name.ToString():
                        #rs.AddArc3Pt(points[0],points[1],points[2])    
                        polycurve.Append(Rhino.Geometry.ArcCurve(Rhino.Geometry.Arc(points[0],points[1],points[2])))
                curves.append(polycurve)
            self.Letters[char]=curves
            self.SizeX[char]=float(xele.Attribute("dX").Value)
            self.SizeY[char]=float(xele.Attribute("dY").Value)
            
        return 

    def GenBreps(self,string,plane,brep_height=5.,brep_zshift=-1,text_height=10):

        scale=1.
        _max_sizey=max([self.SizeY[x] for x in self.SizeY])
        scale=round(text_height/_max_sizey,2)

        breps=[]
        #cplane stuff
        if string!="":
            cplane=plane
            wplane=Rhino.Geometry.Plane.WorldXY
            txt=string.upper()
            
            ip=cplane.Origin 
            for i in range(0,len(txt)):
                if txt[i]in self.Letters:
                    for j in self.Letters[txt[i]]:
                        pc=j.Duplicate()
                        
                        xform=Rhino.Geometry.Transform.Scale(wplane,scale,scale,1.)
                        pc.Transform(xform)
                        
                        cplane.Origin=ip+cplane.ZAxis*brep_zshift
                        xform=Rhino.Geometry.Transform.ChangeBasis(cplane,wplane)
                        pc.Transform(xform)
                        
                        rail=Rhino.Geometry.LineCurve(Rhino.Geometry.Line(cplane.Origin,cplane.Origin+cplane.ZAxis*brep_height))
                        brep=Rhino.Geometry.Brep.CreateFromSweep(rail,pc,True,sc.doc.ModelAbsoluteTolerance)
                        brep=brep[0].CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
                        breps.append(brep)
                        #obj.append(sc.doc.Objects.AddCurve(pc))
                    ip+=cplane.XAxis*(self.SizeX[txt[i]]*scale+self.Spacing*scale)
                elif txt[i]==" ":
                    ip+=cplane.XAxis*self.Spacing*2*scale
                elif txt[i]=="," or txt[i]=="." :
                    ip+=cplane.XAxis*self.Spacing*scale
        else:
            return None
        
        return breps


def test():
    
    test=EasyType()
    obj=test.ConvertText(rs.GetObject("pick txt",rs.filter.annotation))

    return None

def test3D():
    
    test=Text3D()
    #test.GeoToXML()
    #return 
    
    txt=rs.GetObject("pick txt",rs.filter.annotation)
    plane=rs.TextObjectPlane(txt)
    string=rs.TextObjectText(txt)
    for brep in test.GenBreps(string,plane,3,-1,30):
        sc.doc.Objects.AddBrep(brep)

    return None
        
if __name__=="__main__":
    #test()
    test3D()