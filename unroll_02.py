# -*- encoding: utf-8 -*-
"""
Script written by S. Lippert for Seele GmbH
Version 2.0 as of 2018-05-03
Copyright by Seele GmbH
"""

import sys
import os.path as osp
import math
import time
import System

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

#from  signature import EasyType as ET
        
        
class SheetUnroller:
    
    def __init__(self,brep,sheetmarker,mat=0,calcshrink=True):
        self.Error=""
        
        #Checks
        self.Log="init Unroll class...\r\n"
        self.Drawing=None
        t1=time.time()
        
        if mat not in [0,1,2,3]:
            self.Error= "wrong mat code"
            return
            
        if len(sheetmarker)<1:
            self.Error= "no sheetmarker given"
            return
        else:
            if sheetmarker[0].Plane==None:
                self.Error= "no plane in sheetmarker[0]"
                return 
        self.Sheetmarker=sheetmarker
        
        if isinstance(brep,System.Guid):
            brep=rs.coercebrep(brep)
        if not isinstance(brep,Rhino.Geometry.Brep):
            self.Error= "no brep given or cast not sucessfull"
            return 
        if not brep.IsSolid:
            self.Error= "brep is no solid"
            return
        self.Brep=brep
        
        #Start
        t2=time.time()
        self.Log+="1. input validation => OK\r\n"
        self.Log+= "time:" +str(t2-t1)+"\r\n"

        fac=Factory()
        if self.Brep.SolidOrientation!=Rhino.Geometry.BrepSolidOrientation.Outward:
            self.Brep.Flip()
        self.__TestDirection(self.Brep,self.Sheetmarker[0])
        self.Shell,t,id,log=fac.ShellFromSolid(self.Brep,self.Sheetmarker[0].Plane.Origin)
        #sc.doc.Objects.AddBrep(self.Shell)
        #return
        
        #return 
        if self.Shell==None:
            #print "shit"
            self.Error= "no shell extracted"
            return 
            
        self.Log+="2. ShellFromSolid\r\n"
        self.Log+= log
            
        t3=time.time()
        self.Log+=  "time:" +str(t3-t2)+"\r\n"
        
        self.Mat=Mat(t,mat)
        self.BZones=BendingZones(self.Shell,self.Mat)
        t4=time.time()
        self.Log+="3. BendingZones\r\n"
        self.Log+=  self.BZones.Log()
        self.Log+=  "time:" +str(t4-t3)+"\r\n"
        
        #punkte aller markierungen aufsammeln
        cn=0
        self.Points=[]
        for smk in self.Sheetmarker:
            if smk.Points!=[]:
                size=len(smk.Points)
                for i in range(0,size):
                    smk.PointIds.append(cn+i)
                self.Points+=smk.Points
                cn+=size
        
        self.UR=self.__URData()
        if calcshrink:
            shrinks=[x.CalcShrink if x!=None else None for x in self.BZones.FaceParameter]
        else:
            shrinks=[0 if x!=None else None for x in self.BZones.FaceParameter]
        
        self.UR.Breps,self.UR.Axis,self.UR.Points=fac.UnrollShell(self.Shell,shrinks,self.BZones.Groups,self.Points)
        self.UR.Angles=[]
        self.UR.AxisShrink =[]
        
        for x in self.BZones.FaceParameter:
             if x!=None:
                if x.Side==0:
                   self.UR.Angles.append(x.Angle)
                elif x.Side==1:
                   self.UR.Angles.append(x.Angle*-1)
                self.UR.AxisShrink.append(abs(x.TableShrink)/2)
                
        t5=time.time()
        self.Log+="4. UnrollShell\r\n"
        self.Log+=  "time:" +str(t5-t4)+"\r\n"
        
        self.UR.Plane,self.UR.SizeX,self.UR.SizeY=self.__OrientUnroll(self.UR)
        
        t6=time.time()
        self.Log+="5. OrientUnroll\r\n"
        self.Log+=  "time:" +str(t6-t5)+"\r\n"
         
        self.Log+=  "totaltime: " +str(t6-t1)+"\r\n"
        print "Unroll.__init__: " + str(round(t6-t1,2)) +" s"
    
        return True
    
    def __TestDirection(self,shell,sheetmarker):
        
        testpoint=sheetmarker.Plane.Origin
        #rs.AddLine(testpoint,testpoint+sheetmarker.Plane.ZAxis*100)
        threshold=0.5
        vec=None
        for face in shell.Faces:
            rc, u, v = face.ClosestPoint(testpoint)
            d=face.PointAt(u,v).DistanceTo(testpoint)
            fak=1
            if face.OrientationIsReversed:
                fak=-1
            if d<threshold:
                srf=shell.Surfaces[face.SurfaceIndex]
                rc,u,v=srf.ClosestPoint(testpoint)
                vec=srf.NormalAt(u,v)*fak
                #rs.AddLine(testpoint,testpoint+vec*100)
                break
        if vec==None:
            self.Error+="Error while finding normal on brep"
            print "error while flipping"
            return False
        angle=rs.VectorAngle(vec,sheetmarker.Plane.ZAxis)
        print angle
        if angle>10:
            sheetmarker.PlaneFlip()
            print "flipped annotation"
            return True
        print "plane and surfacenormal do match"
        return False
    
    def __OrientUnroll(self,ur):
        
        plane=Rhino.Geometry.Plane(ur.Points[0],ur.Points[1],ur.Points[2])
        #rs.AddPoints(ur.Points)
        a=0
        b=0
        
        xform = Rhino.Geometry.Transform.ChangeBasis(Rhino.Geometry.Plane.WorldXY,plane)
        bbx = Rhino.Geometry.BoundingBox.Empty
        
        #bbx ermitteln & richtig platzieren
        for i in range(0,len(ur.Breps)):
            bbx=Rhino.Geometry.BoundingBox.Union(bbx,ur.Breps[i].GetBoundingBox(xform))
        
        xform = Rhino.Geometry.Transform.ChangeBasis(plane, Rhino.Geometry.Plane.WorldXY)
        corners = list(bbx.GetCorners())
        for pt in corners: pt.Transform(xform)
        
        plane,a,b=self.__GetBBXPLane(corners)
        #xform= Rhino.Geometry.Transform.PlaneToPlane(plane, Rhino.Geometry.Plane.WorldXY)
        xform = Rhino.Geometry.Transform.ChangeBasis(Rhino.Geometry.Plane.WorldXY,plane)
        
        #Objekte richtig orientieren
        for i in range(0,len(ur.Breps)):
            ur.Breps[i].Transform(xform)
            
        for i in range(0,len(ur.Axis)):
            ur.Axis[i].Transform(xform)
        
        for i in range(0,len(ur.Points)):
            ur.Points[i].Transform(xform)
        
        plane.Transform(xform)
        
        return plane,a,b
    
    def __GetBBXPLane(self,pts):
        
        dx=pts[0].DistanceTo(pts[1])
        dy=pts[0].DistanceTo(pts[3])
        if dy>dx:
            return Rhino.Geometry.Plane(pts[3],pts[0],pts[2]),dy,dx
        else:
            return Rhino.Geometry.Plane(pts[0],pts[1],pts[3]),dx,dy
    
    class __URData:
        
        def __init__(self):
            
            self.Breps=None
            self.Axis=None
            self.Angles=None
            self.AxisShrink=None
            self.Points=None
            self.Plane=None
            self.SizeX=None
            self.SizeY=None
            
        def ZipURData(self):
            
            zip=[]
            if self.URSurfaces!=None:
                zip+=self.URSurfaces
            if self.UROutlines!=None:
                zip+=self.UROutlines
            if self.URAxis!=None:
                zip+=self.URAxis
            if self.URGravur!=None:
                zip+=self.URGravur
            
            return zip
    
    class Dim:
        
        def __init__(self,x=None,y=None,z=None):
            self.X=x
            self.Y=y
            self.Z=z
            
    def Dimensions(self):
        
        return self.Dim(round(self.UR.SizeX,1),round(self.UR.SizeY,1),round(self.Mat.T,1))
    
    def GenDrawing(self,lengravaxis=20,secz=False,angletxtheight=8.,sheettxtheight=10.,gravanschlag=False):
        
        
        t1=time.time()
        
        #globangletxtheight=8
        textoffx=5
        
        crv=[]
        lines=[]
        grav=[]
        gravangles=[]
        baxis=[]
        blines=[]
        
        rs.EnableRedraw(False)
        
        for smk in self.Sheetmarker:
            reb=smk.Rebuild(self.UR.Points)
            if smk.Layer==0:
                crv+=reb
            elif smk.Layer==1:
                grav+=reb    
            #print smk.Layer
            
        plane =self.Sheetmarker[0].Plane        
        
        for i in range(0,len(self.UR.Breps)):
            #crvout=Rhino.Geometry.Curve.JoinCurves(self.UR.Breps[i].DuplicateEdgeCurves(True))
            crvout=self.__optimze_boundary(self.UR.Breps[i].DuplicateEdgeCurves(True),1)
            res=Rhino.Geometry.Curve.JoinCurves(crvout,sc.doc.ModelAbsoluteTolerance)
            blines+=[rs.AddTextDot("opencurve!",x.PointAtStart) for x in res if not x.IsClosed]
            
            loops=[]
            for loop in self.UR.Breps[i].Loops:
                if loop.LoopType==Rhino.Geometry.BrepLoopType.Outer:
                    loops.append(loop.To3dCurve())
            
            for j in self.UR.Breps[i].Edges:
                if len(j.AdjacentFaces())==2:
                    rc,pl=j.TryGetPolyline()
                    if rc:
                        blines.append(sc.doc.Objects.AddPolyline(pl))
            
            for j in crvout:
                crv.append(sc.doc.Objects.AddCurve(j))
        
        #Gravuren für die Biegewinkel
        for i in range(0,len(self.UR.Axis)):
            lgravaxis=lengravaxis
            #if angletxtheight=
            #angletxtheight=globangletxtheight
            
            if self.UR.Axis[i]!=None:
                #print "edge for axis{0:d}={1:.2f}".format(i,self.UR.EdgeLength[i])
                
                lines.append(rs.AddLine(self.UR.Axis[i].From,self.UR.Axis[i].To))
                dir=self.UR.Axis[i].Direction
                dir.Unitize()
                
                dist=self.UR.Axis[i].From.DistanceTo(self.UR.Axis[i].To)
                if dist<lgravaxis*2:
                    lgravaxis=dist/2-2
                baxis.append(rs.AddLine(self.UR.Axis[i].From,self.UR.Axis[i].From+dir*lgravaxis))
                baxis.append(rs.AddLine(self.UR.Axis[i].To,self.UR.Axis[i].To-dir*lgravaxis))
                vx=self.UR.Axis[i].Direction
                vx.Unitize()
                vy=Rhino.Geometry.Vector3d.CrossProduct(vx,Rhino.Geometry.Vector3d(0,0,1))*-1
                
                anghelp=self.UR.Angles[i]*-1
                textlen=len(str(round(anghelp,1))*angletxtheight)
                
                if textlen>dist:
                    lgravaxis=0
                    #angletxtheight=6
                elif textlen+lgravaxis+5>dist:
                    lgravaxis=0
                else:
                    lgravaxis+=textoffx
                
                planec=Rhino.Geometry.Plane(self.UR.Axis[i].From+dir*(lgravaxis)-vy*angletxtheight*0.5,vx,vy)
                if anghelp>0:
                    gravangles.append(rs.AddText("+"+str(round(anghelp,1))+"°",planec,angletxtheight))
                else:
                    gravangles.append(rs.AddText(str(round(anghelp,1))+"°",planec,angletxtheight))
                    
        
        if gravanschlag:
            #Gravuren für die Anschlagsmaße
            for i in range(0,len(self.UR.Axis)):
                lgravaxis=lengravaxis
                #if angletxtheight=
                #angletxtheight=globangletxtheight
            
                _crvout=[]
                for _c in crvout:
                    for _l in loops:
                        if _l.PointAt(_l.ClosestPoint(_c.PointAtStart)[1]).DistanceTo(_c.PointAtStart)<1 and _l.PointAt(_l.ClosestPoint(_c.PointAtEnd)[1]).DistanceTo(_c.PointAtEnd)<1:
                            _crvout.append(_c)
                            #rs.ObjectColor(sc.doc.Objects.AddCurve(_c),[0,0,255])
            
                if self.UR.Axis[i]!=None:
                    #print "edge for axis{0:d}={1:.2f}".format(i,self.UR.EdgeLength[i])
                
                    _p=(self.UR.Axis[i].From+self.UR.Axis[i].To)/2
                    _laxis=self.UR.Axis[i].From.DistanceTo(self.UR.Axis[i].To)
                    _closest=[]
                    for _c in _crvout:
                        _lapprox=Rhino.Geometry.Line(_c.PointAtStart,_c.PointAtEnd)
                        try:
                            #if True:
                            _angle=rs.VectorAngle(self.UR.Axis[i].Direction,_lapprox.Direction)
                            _angle=_angle if _angle<90. else 180-_angle
                            _,_t=_c.ClosestPoint(_p)
                            _cp=_c.PointAt(_t)
                            _dist=_p.DistanceTo(_cp)
                            #rs.ObjectColor(rs.AddLine(_p,_cp),[0,0,255])
                            _closest.append([_dist,_cp,_angle,_lapprox,_c])
                        except:
                            continue
                
                    _sclosest=sorted(_closest,key=lambda x:x[0])
                    _lhelp=Rhino.Geometry.Line(_p,_sclosest[0][1])
                    _v=_lhelp.Direction
                    _v.Unitize()
                    _pl=rs.PlaneFromNormal(_lhelp.From+_v*sheettxtheight,Rhino.Geometry.Plane.WorldXY.ZAxis,self.UR.Axis[i].Direction)
                    grav.append(sc.doc.Objects.AddLine(_lhelp))
                    grav.append(rs.AddText(str(round(_lhelp.Length+self.UR.AxisShrink[i],2))+"mm",_pl,sheettxtheight))
                

        
        
        dwg=Drawing(secz)
        dwg.Name=self.Sheetmarker[0].Text
        dwg.Points=self.UR.Points[3:]
        dwg.Plane=self.UR.Plane
        dwg.Outlines=crv
        dwg.Axis=lines
        dwg.Gravur=grav
        dwg.BLines=blines
        dwg.Angles=gravangles
        dwg.BAxis=baxis
        dwg.Update()
        
        rs.EnableRedraw(True)
        
        t2=time.time()
        
        print "Unroll.GenDrawing: " + str(round(t2-t1,2)) +" s"
        
        return dwg
    
    def __optimze_boundary(self,crv,thresh=1):
        
        clong=[]
        cshort=[]
        for i,x in enumerate(crv):
            if x.GetLength()<1:
                cshort.append(x)
            else:
                clong.append(x)
        for cs in cshort:
            kindex=-1
            
            pm=(cs.PointAtStart+cs.PointAtEnd)/2
            for p in [cs.PointAtStart,cs.PointAtEnd]:
                closest = None
                for _j,cl in enumerate(clong):
                    if _j!=kindex:
                        curve = cl
                        rc, t = curve.ClosestPoint(p)
                        if rc:
                            distance = p.DistanceTo( curve.PointAt(t) )
                            if closest is None or distance<closest[0]:
                                closest = distance, cl, curve.PointAt(t), _j
                if closest[2].DistanceTo(closest[1].PointAtStart)<closest[2].DistanceTo(closest[1].PointAtEnd):
                    closest[1].SetStartPoint(pm)
                else:
                    closest[1].SetEndPoint(pm)
                kindex=closest[-1]
                
        return clong

class SheetMarker:
    
    def __init__(self,points=None,text="unset",curve=None,diameter=6,size=10,plane=None,txtheight=10,cross=True,circle=True,font="Arial",layer=1,show=True):
        
        dimstyle=None
        annotation=None
        
        self.Flip=False
        if isinstance(text,System.Guid):
            annotation=rs.coercegeometry(text, True)
        if isinstance(text,Rhino.Geometry.TextEntity):
            annotation=text
        if annotation!=None:
            text=annotation.Text
            plane=annotation.Plane
            fontdata = sc.doc.Fonts[annotation.FontIndex]
            if font!="Arial":
                index = sc.doc.Fonts.FindOrCreate( font, fontdata.Bold, fontdata.Italic )
                annotation.FontIndex = index
        
        self.Show=show
        self.PointIds=[]
        self.CurveId=None
        self.Points=points
        self.Diameter=diameter
        self.Size=size
        self.Text=text #string!
        self.Curve=curve #noch nicht implementiert
        self.Plane=plane
        self.Cross=cross
        self.Circle=circle
        self.Layer=layer
        
        if text!="unset":
            if annotation==None:
                self.Annotation=Rhino.Geometry.TextEntity()
                self.Annotation.Plane=plane
                self.Annotation.Text=text
                self.Annotation.TextHeight=txtheight
                if font!="Arial":
                    index = sc.doc.Fonts.FindOrCreate( font, False, False )
                    self.Annotation.FontIndex = index
            else:
                self.Annotation=annotation.Duplicate()
        
        if self.Plane!=None:
            self.Points=[self.Plane.Origin,self.Plane.Origin+self.Plane.XAxis,self.Plane.Origin+self.Plane.YAxis]
        
    def Rebuild(self,ptrans):

        if not self.Show:
            return []
        newp=[]
        for i in self.PointIds:
            newp.append(ptrans[i])
        if len(newp)==3:
            self.Plane=Rhino.Geometry.Plane(newp[0],newp[1],newp[2])
            if self.Text==None:
                self.Text="txt not spec."
            
            xform=Rhino.Geometry.Transform.PlaneToPlane(self.Annotation.Plane,self.Plane)
            self.Annotation.Transform(xform)
            return [sc.doc.Objects.AddText(self.Annotation)]
        elif len(newp)==1:
            self.Plane=Rhino.Geometry.Plane.WorldXY
            self.Plane.Origin=newp[0]
            if self.Diameter!=0:
                ret=[]
                if self.Circle:
                    ret.append(rs.AddCircle(self.Plane,self.Diameter/2))
                if self.Cross:
                    ret.append(rs.AddLine(self.Plane.Origin+self.Plane.XAxis*-self.Size/2,self.Plane.Origin+self.Plane.XAxis*self.Size/2))
                    ret.append(rs.AddLine(self.Plane.Origin+self.Plane.YAxis*-self.Size/2,self.Plane.Origin+self.Plane.YAxis*self.Size/2))
                return ret
                
        return []
            
    def PlaneFlip(self):
        
        self.Flip=True
        x=self.Text.Length
        y=self.Annotation.DimensionStyle.TextHeight
        self.Plane=rs.RotatePlane(self.Plane,180,self.Plane.YAxis)
        self.Plane.Origin-=self.Plane.XAxis*x*y
        self.Points=[self.Plane.Origin,self.Plane.Origin+self.Plane.XAxis,self.Plane.Origin+self.Plane.YAxis]
        self.Annotation.Plane=self.Plane
        
        return True
    
class Drawing:
    
    def __init__(self,secz=False):
        
        if Rhino.RhinoApp.Name=="Rhinoceros 6":
            sc.doc.ModelSpaceAnnotationScalingEnabled=False
            sc.doc.ModelSpaceTextScale=1
        
        layer=["WHITE","YELLOW","RED","GREEN","UNROLSRF","BBX", "CYAN", "Blue"]
        if secz:
            layer=["DXF_kontura","DXF_gravir","RED","GREEN","UNROLSRF","BBX", "DXF_angles", "DXF_baxis"]
            
        colors=[[255,255,255],[255,255,0],[255,0,0],[0,255,0],[0,0,0],[0,0,0], [0,255,255], [0,0,255]]
        for i in range(0,len(layer)):
            rs.AddLayer(layer[i],color=colors[i]) 
        
        self.Name=None
        self.Plane=None
        self.Layer=layer
        self.Colors=colors
        self.Surfaces=None
        self.Outlines=None
        self.Axis=None
        self.Gravur=None
        self.BLines=None
        self.BBX=None
        self.Angles=None
        self.BAxis=None
        
    def Update(self):
        
        if self.Surfaces!=None:
            rs.ObjectLayer(self.Surfaces,self.Layer[4])
        if self.Outlines!=None:
            rs.ObjectLayer(self.Outlines,self.Layer[0])
        if self.Axis!=None:
            rs.ObjectLayer(self.Axis,self.Layer[2])
        if self.Gravur!=None:
            rs.ObjectLayer(self.Gravur,self.Layer[1])
        if self.BLines!=None:
            rs.ObjectLayer(self.BLines,self.Layer[3])
        if self.BBX!=None:
            rs.ObjectLayer(self.BBX,self.Layer[5])
        if self.Angles!=None:
            rs.ObjectLayer(self.Angles,self.Layer[6])
        if self.BAxis!=None:
            rs.ObjectLayer(self.BAxis,self.Layer[7])
            
        return True
        
    def Export(self,path=None,filename=None,prefix=None,suffix=None,format="dxf"):
        
        if path==None:
            path=osp.dirname(sc.doc.Path)
        if filename==None:
            filename=self.Name
        if prefix!=None:
            filename=prefix+"-"+filename
        if suffix!=None:
            filename=filename+suffix
        
        rs.EnableRedraw(False)
        rs.SelectObjects(self.__Zip())
        rs.Command("-_export " + path+"\\"+filename+"."+format + " _enter")
        rs.UnselectAllObjects()
        rs.EnableRedraw(False)
        
        return True
         
    def ShowBBX(self):
        
        bbx=None
        if self.Plane!=None and self.Outlines!=None:
            cpt=rs.BoundingBox(self.Outlines,self.Plane)
            bbx=rs.AddPolyline(cpt[:4]+[cpt[0]])
            self.BBX=bbx
            self.Update()
        
        return bbx
        
    def AddPunchMarksAtBendingAxis(self,radius=1,offset=5):
        
        pmarks=None
        if self.Axis!=None:
            pmarks=[]
            rs.EnableRedraw(False)
            for ax in self.Axis:
                sp=rs.CurveStartPoint(ax)
                ep=rs.CurveEndPoint(ax)
                vx=ep-sp
                vx.Unitize()
                pmarks.append(rs.AddCircle(sp+vx*offset,radius))
                pmarks.append(rs.AddCircle(ep-vx*offset,radius))
            self.Outlines+=pmarks
            self.Update()    
            rs.EnableRedraw(True)
            
        return pmarks
        
    def TextToPunchMarks(self):
        
        if self.Gravur!=None:
            txt=[i for i in range(0,len(self.Gravur)) if rs.IsText(self.Gravur[i])]
            grv=[]
            if len(txt)>0:
                rs.EnableRedraw(False)
                for i in range(0,len(self.Gravur)):
                    if not i in txt:
                        grv.append(self.Gravur[i])
                et=ET()
                for i in txt:
                    grv+=et.ConvertText(self.Gravur[i])
            
                rs.DeleteObjects([self.Gravur[i] for i in txt])
                self.Gravur=grv
                self.Update()
                rs.EnableRedraw(True)
                
        return None
        
    def __Zip(self):
        
        zip=[]
        if self.Surfaces!=None:
            zip+=self.Surfaces
        if self.Outlines!=None:
            zip+=self.Outlines
        if self.Axis!=None:
            zip+=self.Axis
        if self.Gravur!=None:
            zip+=self.Gravur
        if self.BLines!=None:
            zip+=self.BLines
        if self.Angles!=None:
            zip+=self.Angles
        if self.BAxis!=None:
            zip+=self.BAxis
        
        return zip 
        
    def Move(self,vector):
        
        res=rs.MoveObjects(self.__Zip(),vector)
        
        return res
        
    def GetObjects(self):
        return self.__Zip()
        
class BendingZones:
    
    def __init__(self,brep,sheetmat):
        
        self.SheetMat=sheetmat
        self.Brep=brep
        self.FaceMask=self.GetBendFaceMask(self.Brep)
        self.FaceParameter=self.GetBendFaceParameter(self.Brep,self.FaceMask,self.SheetMat)
        self.Groups=self.GetBendFaceGroups(self.FaceParameter)
        
        return 
        
    def GetBendFaceMask(self,brep):
        
        faceids=[]
        tol=sc.doc.ModelAbsoluteTolerance/2
        for i in range(0,brep.Faces.Count):
            if self.IsCylinder(brep.Faces[i],tol):
                faceids.append(1)
            else:
                faceids.append(0)
            
        return faceids
    
    def FaceCurvature(self,face,uv=None):
        du=face.Domain(0)
        dv=face.Domain(1)
        if uv==None:
            curv=face.CurvatureAt(du[0]+(du[1]-du[0])/2,dv[0]+(dv[1]-dv[0])/2)
        else:
            u=du[0]+(du[1]-du[0])*uv[0]
            v=dv[0]+(dv[1]-dv[0])*uv[1]
            curv=face.CurvatureAt(u,v)
        return curv
        
    def IsCylinder(self,face,tol):
        curv=self.FaceCurvature(face)
        rcu=curv.OsculatingCircle(0).Radius
        rcv=curv.OsculatingCircle(1).Radius
        if 1/rcu>tol or 1/rcv>tol:
            return True
        else:
            return False
        
    def GetBendFaceParameter(self,brep,facemask,sheetmat):
        
        list=[]
        for i in range(0,len(facemask)):
            if facemask[i]==1:
                    
                    radius=None
                    side=None
                    x=brep.Faces[i].AdjacentEdges()
                    srf=brep.Surfaces[brep.Faces[i].SurfaceIndex]
                    curv=self.FaceCurvature(brep.Faces[i])
                    if curv.OsculatingCircle(0).Radius>sc.doc.ModelAbsoluteTolerance:
                        radius=curv.OsculatingCircle(0).Radius
                        curvs=self.FaceCurvature(brep.Faces[i],[0,0.5])
                        curve=self.FaceCurvature(brep.Faces[i],[1,0.5])
                        dir=0
                    else:   
                        radius=curv.OsculatingCircle(1).Radius
                        curvs=self.FaceCurvature(brep.Faces[i],[0.5,0])
                        curve=self.FaceCurvature(brep.Faces[i],[0.5,1])
                        dir=1
                    
                    axis=Rhino.Geometry.Line(curvs.OsculatingCircle(dir).Center,curve.OsculatingCircle(dir).Center)
                    #rs.AddLine(axis.From,axis.To)
                    radius = round(radius,1)
                    
                    edgelength=sorted([[brep.Edges[j].PointAtStart.DistanceTo(brep.Edges[j].PointAtEnd),brep.Edges[j]] for j in brep.Faces[i].AdjacentEdges()],key=lambda x:x[0],reverse=True)
                    vec=[]
                    pts=[]
                    ptest=[]
                    for j in range(0,2):
                        edge=edgelength[j][1]
                        mp=(edge.PointAtStart+edge.PointAtEnd)/2
                        rc,u,v=srf.ClosestPoint(mp)
                        norm=brep.Faces[i].NormalAt(u,v)
                        vec.append(norm)
                        pts.append(mp)
                        ptest.append(mp+norm*radius)
                    if len(vec)==2:
                        angle=rs.VectorAngle(vec[0],vec[1])
                        #wir suchen immer den kantwinkel - da die richtungsvektoren immer nach außenzeigen benoetigen wir das komplement
                        angle=180-angle
                        if rs.Distance(pts[0],pts[1])<rs.Distance(ptest[0],ptest[1]):
                            side=0#außen
                        else:
                            side=1#innen
                    else:
                        angle=None
                        
                    calcshrink,tableshrink,arclen,edgelen,log=sheetmat.GetShrinkByAngle(angle,radius,side)
                    
                    newP=self.BPara()
                    newP.Side=side
                    newP.Radius=radius
                    newP.Axis=axis
                    newP.Angle=angle
                    newP.CalcShrink=calcshrink
                    newP.ArcLength=arclen
                    newP.EdgeLength=edgelen
                    newP.TableShrink=tableshrink
                    newP.Log=log
                    
                    #print str(newP)
                    
                    list.append(newP)
            else:
                list.append(None)
        
        return list
        
    def Log(self):
        log=""
        
        log+="found " + str(len([x for x in self.FaceMask if x==1])) + " bending faces:\r\n" 
        for i in range(0,len(self.FaceParameter)):
            if self.FaceParameter[i]!=None:
                if self.FaceParameter[i].Log!=None:
                    log+="face-"+str(i)+":\r\n"+self.FaceParameter[i].Log + "\r"
        
        return log
    
    def GetBendFaceGroups(self,bpara):
        #sieht nach ob die achsen verschiedener beigezonen gleich liegen 
        #und ob die biegewinkel korrespondieren
        
        baxs=[]
        baids=[]
        bfaceids=[1 if x!=None else None for x in bpara]
        for i in range(0,len(bpara)):
            if bfaceids[i]==1:
                bax=bpara[i]#.Axis
                if len(baxs)==0:
                    baxs.append(bax)
                    baids.append([i])
                else:
                    append=-1
                    for j in range(0,len(baxs)):
                        if round(bax.Angle,1)==round(baxs[j].Angle,1):
                            ds=bax.Axis.DistanceTo(baxs[j].Axis.From,False)
                            de=bax.Axis.DistanceTo(baxs[j].Axis.To,False)
                            #ds=bax.DistanceTo(baxs[j].From,False)
                            #de=bax.DistanceTo(baxs[j].To,False)
                            if abs(ds+de)<1:
                                append=j
                                break
                    if append!=-1:
                        baids[append].append(i)
                    else:
                        baxs.append(bax)
                        baids.append([i])
        
        for i in range(0,len(bfaceids)):
            bfaceids[i]=None
        
        for i in baids:
            bfaceids[i[0]]=i
        
        return bfaceids
        
    class BPara:
        
        def __init__(self,side=None,radius=None,angle=None):
            self.Side=side
            self.Radius=radius
            self.Angle=angle
            self.CalcShrink=None
            self.ArcLength=None
            self.EdgeLength=None
            self.TableShrink=None
            self.Axis=None
            self.Log=None
        
        def __str__(self):
            return "\n".join(["{} = {}".format(key,str(self.__dict__[key])) for key in self.__dict__ if key!="Log"])
                
        
class Mat:
    
    def __init__(self, t=3, mat=0):

        self.Para=[]
        self.T=t
        path=r'G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\seele.Rhino.Common\\'
        if mat==0:
            file='seele_AlMg3.abw'
        elif mat==1:
            file='seele_1.4301.abw'
        elif mat==2:
            file='seele_St37.abw'
        elif mat==3:
            file='seele_CuZn37.abw'
        self.ParaTable=file
        f=open(path+file)
        for line in f:
            if line[0]==str(self.T)[0]:
                spl=[]
                paradic={}
                for i in line.split(" "):
                    if i!="":
                        spl.append(i)
                spl[3].replace("\n","")
                paradic["angle"]=float(spl[1])
                paradic["rad"]=float(spl[2])
                paradic["shrink"]=float(spl[3])
                self.Para.append(paradic)
                
    def GetTableShrinkVal(self,angle1,ri):
        
        angle=round(angle1,0)
        strip=[self.Para[0]["rad"]]
        save=[[self.Para[0]]]
        for i in range(1,len(self.Para)):
                if self.Para[i]["rad"] in strip:
                    save[strip.index(self.Para[i]["rad"])].append(self.Para[i])
                else:
                    strip.append(self.Para[i]["rad"])
                    save.append([self.Para[i]])
        saves=sorted(save, key=lambda x:x[0]["rad"])
        parastrip=None
        for i in range(0, len(saves)):
            if float(saves[i][0]["rad"])>ri:
                parastrip=sorted([[float(x["angle"]),float(x["shrink"])] for x in saves[i]], key=lambda p:p[0])
                break
        if parastrip==None:
            parastrip=sorted([[float(x["angle"]),float(x["shrink"])] for x in saves[len(saves)-1]], key=lambda p:p[0])
            #print "input-ri bigger than max. table-ri -> used biggest table-ri "
        for i in range(0,len(parastrip)):
            if parastrip[i][0]>=angle:
                return parastrip[i][1]
                
        return 0
        
    def GetShrinkByAngle(self,angle,r,side):
        
        if side==1:
            ri=r
            ra=ri+self.T
        elif side==0:
            ra=r
            ri=ra-self.T
        
        calcangel=180.0-float(angle)
        
        angle=float(angle)
        shrink=self.GetTableShrinkVal(calcangel,ri)  #(HICAD Winkel, bei anderen Materialtabellen #angle angeben)
        if shrink!=None:
            #exterior surface 
            if side==0:
                arclength=math.pi*2*ra*(calcangel/360.0)
                if angle<90:
                    edgelength=2*ra 
                else:
                    edgelength=2*ra*math.tan(math.radians(calcangel/2))
            #interior surface
            else:
                arclength=math.pi*2*ri*(calcangel/360.0)
                if angle<90:
                    edgelength=2*ra
                else:
                    edgelength=2*(ra)*math.tan(math.radians(calcangel/2))
                    
            delta=edgelength-arclength
            delta2=shrink+delta
            #delta2=-shrink-arclength

            log="bending & shrink parameter evaluated:" + "\r\n"  
            log+= "\tside: " + str(side) + "\r\n"  
            log+= "\tri: " + str(round(ri,1))+ "\r\n" 
            log+= "\tra: " + str(round(ra,1))+ "\r\n" 
            log+= "\tbending angle: " + str(round(angle,1))+ "\r\n" 
            log+= "\tcalc angle: " + str(round(calcangel,1))+ "\r\n" 
            log+= "\ttable shrink val: " + str(shrink)+ "\r\n" 
            log+= "\tarclength: " + str(round(arclength,2))+ "\r\n" 
            log+= "\ttheo. edgelength: " + str(round(edgelength,2))+ "\r\n" 
            log+= "\tshrink to perform: " + str(round(delta2,2))+ "\r\n" 
            log+= "\tmod. zone width: " + str(round(arclength+delta2,2)) + "\r\n"
            
            print log
            
            
            return delta2,shrink,arclength,edgelength,log
        else:
            return None   
        
        
class Factory:
    
    def __init__(self):
        pass
        
    def ShellFromSolid(self,solid,testpoint,create=False):
        
        """extracts a unrollable surface or polysurface from a solid
        Parameters:
            solid: closed polysurface as brep
            testpoint: identifies the facegroup to extract
            create: [optional] add extracted sheet surface to document
        Returns:
            shell Rhino.Geometry.Brep
            solid thickness as float
            objid if created
        """
        
        log=""
        
        threshold=0.2
        angtol = sc.doc.ModelAngleToleranceDegrees 
        tol = sc.doc.ModelAbsoluteTolerance 
        brep=rs.coercebrep(solid)
        
        #evaluate all brep-edge angles
        edgemask=[]
        for i in range(0,brep.Edges.Count):
            angle=self.GetFaceAngle(brep,i)
            if angle<angtol or abs(angle-180)<angtol:
                edgemask.append(1)
            else:
                edgemask.append(0)
                
        facemask=[1 for x in range(0,brep.Faces.Count)]
        
        topogrps=[]
        #group faces with tangent transitions in between
        for i in range(0,brep.Faces.Count):
            topogrp=[]
            self.GetTopoFaces(brep,i,topogrp,facemask,edgemask)
            if topogrp!=[]:
                topogrps.append(topogrp)
        
        log+="\tfound "+ str(len(topogrps)) +" tangetially continuouse topogroups\r\n"
        
        #identify ***THECHOSENONE*** by testpoint
        resgrp=None
        for i in range(0,len(topogrps)):
            for face in topogrps[i]:
                rc, u, v = face.ClosestPoint(testpoint)
                d=face.PointAt(u,v).DistanceTo(testpoint)
                if d<threshold:
                    resgrp=i
                    break
            if resgrp!=None:
                break
        if resgrp==None:
            return None,None,None,None
            
        #gefundene shells in breps umwandeln
        shells=[]
        for i in range(0,len(topogrps)):
            shell=Rhino.Geometry.Brep.DuplicateSubBrep(solid,[x.FaceIndex for x in topogrps[i]])
            shells.append(shell)
        shell=shells[resgrp]
        shells.pop(resgrp)
        
        #alle uebrigen shells nach area sortieren
        t=0
        list=[]
        for i in range(0,len(shells)):
            area=shells[i].GetArea()
            list.append([i,area])
        
        lss=sorted(list, key=lambda x:x[1],reverse=True)
        shell1=shells[lss[0][0]]
        
        pp=shell.ClosestPoint(testpoint)
        pp1=shell1.ClosestPoint(testpoint)
        
        t=round(pp.DistanceTo(pp1),1)
        log+="\teval. sheet thickness= " +str(round(t,1)) +"\r\n"

        #build geometry
        oid=None
        if create==True: 
            oid=sc.doc.Objects.AddBrep(shell)
            
        return shell,t,oid,log
        
    def UnrollShell(self,brep,bshrinks,bgroups,points):
        """
        Parameters:
          brep = string z.B. Profil QS Name
          t = string z.B. Profil QS Name
          mat = instance of SheetMat Class
          points = list[Point3d]
          
        Returns:
          NCCollection object  
        """
        
        tol=sc.doc.ModelAbsoluteTolerance
                
        unroll=Rhino.Geometry.Unroller(brep)
        #sc.doc.Objects.AddBrep(brep)
        unroll.ExplodeOutput=False
        breps, curves, pointsout, dots=unroll.PerformUnroll()
        
        dots=[]
        dot3d=[]
        for i in range(0,len(points)):
            dot3d.append(Rhino.Geometry.TextDot(str(i),points[i]))
            unroll.AddFollowingGeometry(Rhino.Geometry.TextDot(str(i),points[i]))
        
        breps, curves, pointsout, dots = unroll.PerformUnroll()
        
        pointfaceids=[]
        pointfaceuv=[]
        dic={}
        pointsout=[]
        for i in dots:
            dic[i.Text]=i.Point
        for i in range(0,len(points)):
            if str(i) in dic:
                pointsout.append(dic[str(i)])
            else:
                rs.AddTextDot("Error",dot3d[i].Point)
        for p in pointsout:
            for i in range(0,brep.Faces.Count):
                rc,u,v=breps[i].Faces[0].ClosestPoint(p)
                closestp=breps[i].Faces[0].PointAt(u,v)
                if closestp.DistanceTo(p)<tol:
                    pointfaceids.append(i)
                    pointfaceuv.append([u,v])
                    break
        
        newbrep=Rhino.Geometry.Brep.JoinBreps([i.Faces[0].DuplicateFace(False) for i in breps],tol)
        
        if len(newbrep)==1:
            newbrep=newbrep[0]
        else:
            print "non connected unroll"
            return breps,None,None
            
        vz=Rhino.Geometry.Vector3d.ZAxis
        for i in range(0,len(bgroups)):
            if bgroups[i]!=None:
                bendingaxis,zonewidth=self.GetBendingAxis(breps[i])
                
                shrink=bshrinks[i]
                #print zonewidth
                shrink*=-1
                
                vx=bendingaxis.Direction
                vy=Rhino.Geometry.Vector3d.CrossProduct(vx,vz)
                pl=Rhino.Geometry.Plane(bendingaxis.From,vx,vy)
                
                newzonesize=zonewidth-shrink
                factor=newzonesize/zonewidth
                xt=Rhino.Geometry.Transform.Scale(pl,1.0,factor,1.0)
                edges=[]
                for j in bgroups[i]:
                    breps[j].Transform(xt)
                    
                    #newbrep für die gruppenlogik // brep für die shrink berechnung...
                    #evtl. bei sehr kurzen biegezonen nicht nach länge sortieren sondern nach winkel zur biegeachse, da wir ja die kanten parallel zur biegeachse suchen.
                    edgeidsbreps=sorted([[breps[j].Edges[k].PointAtStart.DistanceTo(breps[j].Edges[k].PointAtEnd),k] for k in breps[j].Faces[0].AdjacentEdges()],key=lambda x:x[0],reverse=True)
                    edgeids=sorted([[newbrep.Edges[k].PointAtStart.DistanceTo(newbrep.Edges[k].PointAtEnd),k] for k in newbrep.Faces[j].AdjacentEdges()],key=lambda x:x[0],reverse=True)
                    
                    ptestAbrep=(breps[j].Edges[edgeidsbreps[0][1]].PointAtStart+breps[j].Edges[edgeidsbreps[0][1]].PointAtEnd)/2
                    ptestBbrep=(breps[j].Edges[edgeidsbreps[1][1]].PointAtStart+breps[j].Edges[edgeidsbreps[1][1]].PointAtEnd)/2
                    ptestAnew=(newbrep.Edges[edgeids[0][1]].PointAtStart+newbrep.Edges[edgeids[0][1]].PointAtEnd)/2
                    ptestBnew=(newbrep.Edges[edgeids[1][1]].PointAtStart+newbrep.Edges[edgeids[1][1]].PointAtEnd)/2
                    mpnew=(ptestAnew+ptestBnew)/2
                    mpbrep=(ptestAbrep+ptestBbrep)/2
                    
                    dm=mpbrep-mpnew
                    ptestAnew+=dm
                    ptestBnew+=dm
                    
                    aa=ptestAnew.DistanceTo(ptestAbrep)
                    ab=ptestAnew.DistanceTo(ptestBbrep)
                    if aa>ab:
                        a=edgeids[0][1]
                        b=edgeids[1][1]
                        edgeids[0][1]=b
                        edgeids[1][1]=a
                    
                    vA = (breps[j].Edges[edgeidsbreps[0][1]].PointAtStart+breps[j].Edges[edgeidsbreps[0][1]].PointAtEnd)/2 - pl.Origin;
                    vB = (breps[j].Edges[edgeidsbreps[1][1]].PointAtStart+breps[j].Edges[edgeidsbreps[1][1]].PointAtEnd)/2 - pl.Origin;
                    cooA=Rhino.Geometry.Point3d(vA*pl.XAxis, vA*pl.YAxis, vA*pl.ZAxis)
                    cooB=Rhino.Geometry.Point3d(vB*pl.XAxis, vB*pl.YAxis, vB*pl.ZAxis)
                    
                    if cooA.Y<0:
                        edges.append([edgeids[0][1],edgeids[1][1]])
                    else:
                        edges.append([edgeids[1][1],edgeids[0][1]])
                        
                #find adjacent faces A
                topogrpA=[]
                for j in bgroups[i]:
                    facemask=[1 for x in range(0,newbrep.Faces.Count)]
                    edgemask=[1 for x in range(0,newbrep.Edges.Count)]
                    for k in edges:
                        edgemask[k[0]]=0
                    grp=[]
                    self.GetTopoFaces(newbrep,j,grp,facemask,edgemask)
                    grp.pop(0)
                    topogrpA+=grp
    
                #find adjacent faces B
                topogrpB=[]
                for j in bgroups[i]:
                    facemask=[1 for x in range(0,newbrep.Faces.Count)]
                    edgemask=[1 for x in range(0,newbrep.Edges.Count)]
                    for k in edges:
                        edgemask[k[1]]=0
                    grp=[]
                    self.GetTopoFaces(newbrep,j,grp,facemask,edgemask)
                    grp.pop(0)
                    topogrpB+=grp
                
                grpshiftB=[]
                grpshiftA=[]
                for face in topogrpA:
                    if (not face.FaceIndex in grpshiftA) and (not face.FaceIndex in bgroups[i])  :
                        grpshiftA.append(face.FaceIndex)
                for face in topogrpB:
                    if (not face.FaceIndex in grpshiftB) and (not face.FaceIndex in bgroups[i]):
                        grpshiftB.append(face.FaceIndex)
                        
                vecA=pl.YAxis*shrink/2*-1
                xt=Rhino.Geometry.Transform.Translation(vecA.X,vecA.Y,0)
                for brpid in grpshiftA:
                    breps[brpid].Transform(xt)
                    
                vecB=pl.YAxis*shrink/2
                xt=Rhino.Geometry.Transform.Translation(vecB.X,vecB.Y,0)
                for brpid in grpshiftB:
                    breps[brpid].Transform(xt)
                    
        bendingaxis=[]
        for i in range(0,len(bshrinks)):
            if bshrinks[i]!=None:
                bax,zw=self.GetBendingAxis(breps[i])
                bendingaxis.append(bax)
        
        for i in range(0,len(pointsout)):
            pointsout[i]=breps[pointfaceids[i]].Faces[0].PointAt(pointfaceuv[i][0],pointfaceuv[i][1])
            
        joinedbreps=Rhino.Geometry.Brep.JoinBreps([i.Faces[0].DuplicateFace(False) for i in breps],tol)
        
        
        return joinedbreps,bendingaxis,pointsout
        
    def GetTopoFaces(self,brep,faceid,grp,facemask,edgemask):
        """utility to get a group of faces depending on the edge properties represented by edgemask
        -> inverted edgemask to the one used by SheetSrfFromSolid would result in groups consiting of non tangent faces separated by tangent faces
        """
        if facemask[faceid]==1:
            grp.append(brep.Faces[faceid])
            facemask[faceid]=0
            edges=[i for i in brep.Faces[faceid].AdjacentEdges() if edgemask[i]==1]
            faceids=[]
            for i in edges:
                res=brep.Edges[i].AdjacentFaces()
                for j in res:
                    if j!=faceid:
                        faceids.append(j)
            for i in faceids:
                self.GetTopoFaces(brep,i,grp,facemask,edgemask)
        
        return None
        
    def GetFaceAngle(self,brep,edgeid):
        p=brep.Edges[edgeid].PointAtStart
        #rc,t=brep.Edges[edgeid].ClosestPoint((brep.Edges[edgeid].PointAtStart+brep.Edges[edgeid].PointAtEnd)/2)
        #p=brep.Edges[edgeid].PointAt(t)
        vec=[]
        for i in brep.Edges[edgeid].AdjacentFaces():
            srf=brep.Surfaces[brep.Faces[i].SurfaceIndex]
            rc,u,v=srf.ClosestPoint(p)
            vec.append(srf.NormalAt(u,v))
        if len(vec)==2:
            angle=rs.VectorAngle(vec[0],vec[1])
        else:
            angle=90.0
        return round(angle,1)
        
    def GetBendingAxis(self,brep):
        
        axis=None
        zonewidth=None
        
        linesUS=[]
        if brep.Edges.Count!=4:
            linesUS=self.__StripEdges(brep.Edges)
        else:
            for i in range(0,brep.Edges.Count):
                linesUS.append(Rhino.Geometry.Line(brep.Edges[i].PointAtStart,brep.Edges[i].PointAtEnd))
                
        lines=sorted([[x.From.DistanceTo(x.To),x] for x in linesUS],key=lambda x:x[0],reverse=True)
        lines=[x[1] for x in lines[:2]]
        
        pps=lines[0].ClosestPoint(lines[1].From,False)
        ppe=lines[0].ClosestPoint(lines[1].To,False)
        ds=pps.DistanceTo(lines[1].From)
        de=ppe.DistanceTo(lines[1].To)
        pms=(pps+lines[1].From)/2
        pme=(ppe+lines[1].To)/2
        axis=Rhino.Geometry.Line(pms,pme)
        zonewidth=ds
        

        
        return axis,zonewidth
        
    def __StripEdges(self,edges,thresh=0.5):
        
        lines=[]
        angles=[]
        for i in range(0,edges.Count):
            lines.append(Rhino.Geometry.Line(edges[i].PointAtStart,edges[i].PointAtEnd))
        lines.append(lines[0])
        for i in range(0,len(lines)-1):
            angles.append(rs.VectorAngle(lines[i].Direction,lines[i+1].Direction))
        lines.pop()
        cn=0
        for i in range(0,len(angles)):
            if angles[i]>thresh:
                cn=i+1
                break
        ls1=lines[cn:]
        ls2=lines[:cn]
        ls2.reverse
        lines=ls1+ls2
        ls1=angles[cn:]
        ls2=angles[:cn]
        ls2.reverse
        angles=ls1+ls2
        
        grps=[]
        grp=[]
        for i in range(0,len(angles)):
            grp.append(lines[i])
            if angles[i]>=thresh:
                grps.append(grp)
                grp=[]
        if grp!=[]:
            grps.append(grp)
        lines=[]
        for grp in grps:
            lines.append(Rhino.Geometry.Line(grp[0].From,grp[len(grp)-1].To))
        return lines
        
        
def example(obj,mat):
    target = rs.BrowseForFolder(message = "Choose folder to save dxfs")
    txt=[x for x in obj if rs.IsText(x)]
    brp=[x for x in obj if rs.IsPolysurface(x)]
    pt=[rs.PointCoordinates(x) for x in obj if rs.IsPoint(x)]
    
    cooy=1000
    step=1000
    for x in txt:
        co=rs.PointClosestObject(rs.TextObjectPoint(x),brp)
        #rs.TextObjectText(x,rs.ObjectName(co[0])[6:])
        sheetmarker=[SheetMarker(text=x)]
        #sheetmarker=[SheetMarker(text="jaqueline",plane=rs.TextObjectPlane(x),font="Laser sans Serif",txtheight=25 )]
        
        co=rs.PointClosestObject(sheetmarker[0].Plane.Origin,brp)
        
        if rs.Distance(sheetmarker[0].Plane.Origin,co[1])<1:
            ptss=[]
            for i in pt:
                co1=rs.PointClosestObject(i,co[0])
                if rs.Distance(co1[1],i)<1:
                    sheetmarker.append(SheetMarker(points=[co1[1]],diameter=5.1,cross=False,circle=True,layer=1))
                    #sheetmarker.append(SheetMarker(points=[co1[1]],diameter=15.5,cross=False,circle=True,layer=1))
            
            ur=SheetUnroller(rs.coercebrep(co[0]),sheetmarker=sheetmarker,mat=mat)    
        
            dim=ur.Dimensions()
            #print "unrol dimensions x: " + str(dim.X) + " y: " + str(dim.Y) + " z: " + str(dim.Z) 
            dwg=ur.GenDrawing(lengravaxis=5,angletxtheight=5)
            
            
            """for d in dwg.Outlines:
                #rs.SelectObject(d)
                if rs.IsCurve(d):
                    if 16<rs.CurveLength(d)<16.1:
                        rs.ObjectLayer(d, "YELLOW")"""
            
            #dwg.ShowBBX()
            #dwg.AddPunchMarksAtBendingAxis(radius=0.5,offset=2)
            #dwg.TextToPunchMarks()
            #dwg.Export(path=r"C:\Users\schuster_simon\Desktop\DXF",prefix="",suffix="")
            dwg.Export(path=target)
            dwg.Move(Rhino.Geometry.Vector3d(0,cooy,0))
            cooy+=step
        
    return 0 
        
        
if __name__== "__main__":
    example(rs.GetObjects("pick solid and text"),rs.GetInteger("enter material code: 0=AL || 1=VA || 2=ST || 3=CU",number=0,minimum=0,maximum=3))