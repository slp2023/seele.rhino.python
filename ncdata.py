# -*- encoding: utf-8 -*-
"""
Script written by S. Lippert for Seele GmbH
Version 2.0 as of 2018-05-03
Copyright by Seele GmbH
"""
import sys
import clr
from System import IO
from System import Array

#sys.path.append(r"G:\DAT\TECHARCH\TB-Entwicklungen\NcData\NcData\bin\Debug")  
clr.AddReferenceToFileAndPath(r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\seele.Rhino.Common\NcData.dll")
#sys.path.append(r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\seele.Rhino.Common")  
#clr.AddReference ("NcData.dll") 
import NcData  
import rhinoscriptsyntax as rs
import Rhino

class NCCollection:
    
    def __init__(self,name):
        """
        Parameters:
          name = string z.B. Profil QS Name
        Returns:
          NCCollection object  
        """
        self.Name=name
        self.Staebe=NcData.seeleNC.NcTable()
        self.Counts=[]
        self.Abrufliste=[["PARTNAME","QTY","PROFILNAME","BOUNDINGBOX-L","BOUNDINGBOX-B","BOUNDINGBOX-H"]]

    def Add(self,item):
        """
        Parameters:
          item = NCData.NCItem
        """
        self.Staebe.AddModel(item.Model)
        self.Counts.append(item.Count)
        #print item.Count

    def ExportCSV(self,path):
        """
        exports Stabliste und Abrufiste als CSV in das angegebene Verzeichnis
        Parameters:
          path = string Directory
        """
        if len(self.Staebe.Models)>0:
            stb,abr=self._StripDuplicates();
            stb.WriteToFile(IO.FileInfo(path+"\\" +self.Name + ".csv"))
            f=open(path+"\\"+self.Name+"_Abrufliste.csv","w")
            f.write(self._ListToString(abr,"\r",";"))
            f.close()
            
    def SplitExportCSV(self,path,sufixes=""):
        
        if sufixes=="":
            sufixes=["ELU3","ELU4"]
        
        if len(self.Staebe.Models)>0:
            count=len(self.Staebe.Models)
            
            res=count%len(sufixes)
            grp=int(count/len(sufixes))
            
            cn=0
            mod=0
            for i in range(0,len(sufixes)):
                gr1=NcData.seeleNC.NcTable()
                for j in range(0,grp+mod):
                    model=self.Staebe.Models[cn]
                    model.profilename+="_"+sufixes[i]
                    gr1.AddModel(model)
                    cn+=1
                if res!=0:
                    if mod==0:
                        mod=1
                    else:
                        mod=0
                name=self.Name +"_"+sufixes[i]
                stb,abr=self._StripDuplicates(gr1.Models)
                stb.WriteToFile(IO.FileInfo(path+"\\" +name + ".csv"))
                f=open(path+"\\"+name+"_Abrufliste.csv","w")
                f.write(self._ListToString(abr,"\r",";"))
                f.close()
                
        return 0

    def _ListToString(self,list,rowDelimiter,colDelimiter):
        
        string=""
        for row in list:
            for column in row:
                string += str(column) + colDelimiter
            string+=rowDelimiter
            
        return string.replace(".",",")
        
    def _StripDuplicates(self,models=None):
        stripTab = NcData.seeleNC.NcTable()
        stripMod = []
        count = []
        
        if models==None:
            models=self.Staebe.Models
        
        for i,mod in enumerate(models):
            res = False
            for j in range(0,len(stripMod)):
                if stripMod[j].partname == mod.partname:
                    res = True
                    count[j]+=self.Counts[i]
                    break
            if not res:
                stripMod.Add(mod)
                count.Add(self.Counts[i])
                
        abrufliste=[["PARTNAME","QTY","PROFILNAME","BOUNDINGBOX-L","BOUNDINGBOX-B","BOUNDINGBOX-H"]]
        for i in range(0,len(stripMod)):
            stripTab.AddModel(stripMod[i])
            abrufliste.Add([stripMod[i].partname,count[i].ToString(),stripMod[i].profilename,stripMod[i].bblength,stripMod[i].bbwidth,stripMod[i].bbheight])
        
        if models==None:
            self.Staebe=stripTab
            self.Abrufliste=abrufliste
            
        return stripTab,abrufliste
            
            
class NCItem:
    
    def __init__(self,plane, posNo, profilNo, bbx,vis=False,visparentlayer="",count=1):
        """
        Parameters:
          plane = beam Coordinate System
          posNo = ID
          profilNo= WN/Profile Name
          bbx = BoundingBox dimensions list[float]([l,w,h])
        Returns:
          NCItem object 
        """
        #rs.AddPlaneSurface(plane,50,50)
        
        self.WN=profilNo
        self.CPlane= plane
        self.Model=NcData.seeleNC.NcModel(posNo,profilNo,bbx[0],bbx[1],bbx[2])
        self.Count=count
        self.Log= posNo + " NCItem created successfully\r\n"
        self.Vis=vis
        
        if vis:
            bbpts=[]
            bbpts.append(self.CPlane.Origin)
            bbpts.append(bbpts[0]+self.CPlane.XAxis * self.Model.bblength)
            bbpts.append(bbpts[1]+self.CPlane.YAxis * self.Model.bbwidth)
            bbpts.append(bbpts[0]+self.CPlane.YAxis * self.Model.bbwidth)
            bbpts.append(bbpts[0]+self.CPlane.ZAxis * -self.Model.bbheight)
            bbpts.append(bbpts[1]+self.CPlane.ZAxis * -self.Model.bbheight)
            bbpts.append(bbpts[2]+self.CPlane.ZAxis * -self.Model.bbheight)
            bbpts.append(bbpts[3]+self.CPlane.ZAxis * -self.Model.bbheight)
            pl=rs.AddPolyline([bbpts[0],bbpts[1],bbpts[2],bbpts[6],bbpts[7],bbpts[4]])
            self._VisNCData(pl,parentlayer=visparentlayer)        
    
    def AddSaw(self,plane, name = "",cutspace=0,yzCut=0,vis=False,axisx=None,axisy=None,reverse=False,shrink=0,nachlauf=0,visparentlayer=""):
        """
        Parameters:
          plane = Rhino.Geometry.Plane
          name = string
          cutspace= float (mm)
          yzCut=int {0;1} (cut along y/z)
          vis=bool
        """
        bbpts=[]
        bbpts.append(self.CPlane.Origin)
        bbpts.append(bbpts[0]+self.CPlane.XAxis * self.Model.bblength)
        bbpts.append(bbpts[1]+self.CPlane.YAxis * self.Model.bbwidth)
        bbpts.append(bbpts[0]+self.CPlane.YAxis * self.Model.bbwidth)
        bbpts.append(bbpts[0]+self.CPlane.ZAxis * -self.Model.bbheight)
        bbpts.append(bbpts[1]+self.CPlane.ZAxis * -self.Model.bbheight)
        bbpts.append(bbpts[2]+self.CPlane.ZAxis * -self.Model.bbheight)
        bbpts.append(bbpts[3]+self.CPlane.ZAxis * -self.Model.bbheight)

        testmp=(bbpts[6]+bbpts[4])*0.5
        #rs.AddTextDot("",testmp)
        
        vec = rs.PlaneClosestPoint(plane,testmp) -testmp
        vec.Unitize()
        if cutspace != 0:
            plane = rs.PlaneFromNormal(plane.Origin - vec * cutspace, vec)
        
        if axisx==None and axisy==None:
            edges=[]
            edges.append([bbpts[0],bbpts[1]])#0 x-dir 
            edges.append([bbpts[1],bbpts[2]])#1 
            edges.append([bbpts[2],bbpts[3]])#2 x-dir
            edges.append([bbpts[3],bbpts[0]])#3
            
            edges.append([bbpts[4],bbpts[5]])#4 x-dir
            edges.append([bbpts[5],bbpts[6]])#5
            edges.append([bbpts[6],bbpts[7]])#6 x-dir
            edges.append([bbpts[7],bbpts[0]])#7
            
            edges.append([bbpts[0],bbpts[4]])#8 z-dir
            edges.append([bbpts[1],bbpts[5]])#9 z-dir
            edges.append([bbpts[2],bbpts[6]])#10 z-dir
            edges.append([bbpts[3],bbpts[7]])#11 z-dir
            
            #Schnitt in y richtung
            if yzCut==0: 
                line1=edges[4]
                line2=edges[6]
                line3=edges[0]#zustellung
                line4=edges[2]
                
            #Schnitt in -z richtung
            elif yzCut==1:
                line1=edges[2]
                line2=edges[6]
                line3=edges[0]#zustellung
                line4=edges[4]
                
            #Schnitt in x richtung
            elif yzCut==2:
                line1=edges[11]
                line2=edges[10]
                line3=edges[8]#zustellung
                line4=edges[9]
            
            if reverse==False:
                int1=rs.LinePlaneIntersection(line1,plane)
                int2=rs.LinePlaneIntersection(line2,plane)
                int3=rs.LinePlaneIntersection(line3,plane)
            else:
                int1=rs.LinePlaneIntersection(line2,plane)
                int2=rs.LinePlaneIntersection(line1,plane)
                int3=rs.LinePlaneIntersection(line4,plane)
            
            vh=int2-int1
            vh.Unitize()
            int1+=vh*shrink
            int2-=vh*shrink
            int3+=vh*shrink
            
            vh=int1-int3
            vh.Unitize()
            int1+=vh*nachlauf
            int2+=vh*nachlauf
            
            
            
        else:
            
            int1 = axisx[0] 
            int2 = axisx[1]
            int3 = axisy[1]
            
        int1lok = rs.XformWorldToCPlane(int1,self.CPlane)
        int2lok = rs.XformWorldToCPlane(int2,self.CPlane)
        int3lok = rs.XformWorldToCPlane(int1 + vec * 100,self.CPlane)
        
        veclok =  int3lok-int1lok
        veclok.Unitize()
        
        if vis or self.Vis:
            #pl=rs.PlaneFromPoints(int1,int2,int4)
            #srf=rs.AddPlaneSurface(pl,rs.Distance(int1,int2),rs.Distance(int3,int4))
            pl=rs.AddPolyline([int3+vec*10,int3,int1,int2])
            rs.CurveArrows(pl,2)
            self._VisNCData(pl,"saw_" +name,visparentlayer)
                
        self.Model.workdata.Add(NcData.seeleNC.sawtype(name, self._ConvertPointToArray(int1lok), self._ConvertPointToArray(int2lok), self._ConvertPointToArray(veclok)))
        self.Log += "added saw " + name + "...\r\n"
    
        return True

    def AddHole(self, pt1, pt2, name = "",vis=False,visparentlayer=""):
        """
        Parameters:
          pt1 = List[double,double,double] Insert pt
          pt2 = List[double,double,double] Depth pt 
          name= string
        """
        
        pt1lok = rs.XformWorldToCPlane(pt1,self.CPlane)
        pt2lok = rs.XformWorldToCPlane(pt2,self.CPlane)
        self.Model.workdata.Add(NcData.seeleNC.holetype(name, self._ConvertPointToArray(pt1lok), self._ConvertPointToArray(pt2lok)))
        self.Log += "added hole " + name + "...\r\n"
        
        if vis or self.Vis:
            line=rs.AddLine(pt1,pt2)
            self._VisNCData(line,"hole_" +name,visparentlayer)
            rs.CurveArrows(line,2)

    def AddEHole(self, pt1, pt2, pt3, name = "",vis=False,visparentlayer=""):
        """
        Parameters:
          pt1 = List[double,double,double] Insert pt
          pt2 = List[double,double,double] Depth pt  
          pt3 = List[double,double,double] Direction pt 
          name= string
        """
        pt1lok = rs.XformWorldToCPlane(pt1,self.CPlane)
        pt2lok = rs.XformWorldToCPlane(pt2,self.CPlane)
        pt3lok = rs.XformWorldToCPlane(pt3,self.CPlane)
        self.Model.workdata.Add(NcData.seeleNC.eholetype(name, self._ConvertPointToArray(pt1lok), self._ConvertPointToArray(pt2lok), self._ConvertPointToArray(pt3lok)))
        self.Log += "added ehole " + name + "...\r\n"
        
        if vis or self.Vis:
            line=rs.AddPolyline([pt1, pt2, pt3])
            self._VisNCData(line,"ehole_" +name,visparentlayer)
            rs.CurveArrows(line,2)

    def AddRHole(self, pt1, pt2, pt3, name = "",vis=False,visparentlayer=""):
        """
        Parameters:
          pt1 = List[double,double,double] Insert pt
          pt2 = List[double,double,double] Depth pt  
          pt3 = List[double,double,double] Direction pt 
          name= string
        """
        pt1lok = rs.XformWorldToCPlane(pt1,self.CPlane)
        pt2lok = rs.XformWorldToCPlane(pt2,self.CPlane)
        pt3lok = rs.XformWorldToCPlane(pt3,self.CPlane)
        self.Model.workdata.Add(NcData.seeleNC.rholetype(name, self._ConvertPointToArray(pt1lok), self._ConvertPointToArray(pt2lok), self._ConvertPointToArray(pt3lok)))
        self.Log += "added rhole " + name + "...\r\n"
        
        if vis or self.Vis:
            line=rs.AddPolyline([pt1, pt2, pt3])
            self._VisNCData(line,"rhole_" + name,visparentlayer)
            rs.CurveArrows(line,2)

    def AddText(self, pt1,  pt2,  pt3, text, name = "",vis=False,dez=3,visparentlayer=""):
        """
        Parameters:
          pt1 = List[double,double,double] Insert pt
          pt2 = List[double,double,double] Direction pt
          pt3 = List[double,double,double] Orientation pt 
          text = string
          name= string
        """
        pt1lok = rs.XformWorldToCPlane(pt1,self.CPlane)
        pt2lok = rs.XformWorldToCPlane(pt2,self.CPlane)
        pt3lok = rs.XformWorldToCPlane(pt3,self.CPlane)

        vec = pt3lok- pt1lok
        vec.Unitize()

        #pt1lok.X=pt1lok.X#round(pt1lok.X,dez)
        #pt1lok.Y=round(pt1lok.Y,dez)
        #pt1lok.Z=round(pt1lok.Z,dez)
        
        #pt2lok.X=round(pt2lok.X,dez)
        #pt2lok.Y=round(pt2lok.Y,dez)
        #pt2lok.Z=round(pt2lok.Z,dez)
        
        #vec.X=round(vec.X,dez)
        #vec.Y=round(vec.Y,dez)
        #vec.Z=round(vec.Z,dez)
        
        self.Model.workdata.Add(NcData.seeleNC.gtexttype(name, self._ConvertPointToArray(pt1lok), self._ConvertPointToArray(pt2lok), self._ConvertPointToArray(vec), text))
        self.Log += "added gtext " + name + "...\r\n"
        
        if vis or self.Vis:
            line=rs.AddPolyline([pt1, pt2, pt3])
            self._VisNCData(line,"gtext_" + name,visparentlayer)
            rs.CurveArrows(line,2)

    def AddFreemill(self, pt1,  pt2,  pt3, name = "",vis=False,dez=3,visparentlayer=""):
        """
        Parameters:
          pt1 = List[double,double,double] Insert pt
          pt2 = List[double,double,double] Direction pt
          pt3 = List[double,double,double] Orientation pt 
          text = string
          name= string
        """
        
        pt1lok = rs.XformWorldToCPlane(pt1,self.CPlane)
        pt2lok = rs.XformWorldToCPlane(pt2,self.CPlane)
        pt3lok = rs.XformWorldToCPlane(pt3,self.CPlane)
        
        pt1lok.X=round(pt1lok.X,dez)
        pt1lok.Y=round(pt1lok.Y,dez)
        pt1lok.Z=round(pt1lok.Z,dez)
        
        pt2lok.X=round(pt2lok.X,dez)
        pt2lok.Y=round(pt2lok.Y,dez)
        pt2lok.Z=round(pt2lok.Z,dez)
        
        pt3lok.X=round(pt3lok.X,dez)
        pt3lok.Y=round(pt3lok.Y,dez)
        pt3lok.Z=round(pt3lok.Z,dez)
        
        
        self.Model.workdata.Add(NcData.seeleNC.freemilltype(name, self._ConvertPointToArray(pt1lok), self._ConvertPointToArray(pt2lok), self._ConvertPointToArray(pt3lok)))
        self.Log += "added freemill " + name + "...\r\n"
        
        if vis or self.Vis:
            line=rs.AddPolyline([pt1, pt2, pt3])
            self._VisNCData(line,"freemillhole_" + name,visparentlayer)
            rs.CurveArrows(line,2)
        
    def _ConvertPointToArray(self,point):
        return Array [float]([point[0],point[1],point[2]])
    
    def _ConvertCommonPlaneToList(self,plane):
        return([plane.Origin,plane.XAxis,plane.YAxis,plane.ZAxis])
        
    def _VisNCData(self,guid,name="",parentlayer=""):
        if parentlayer!="":
            tempname=rs.AddLayer("NCData-"+self.WN,parent=parentlayer)
        else:
            tempname=rs.AddLayer("NCData-"+self.WN)
        rs.LayerVisible(tempname,False)
        rs.ObjectName(guid,name)
        rs.ObjectLayer(guid,tempname)


class NCWItem:
    
    def __init__(self,posno,plane,bbx):   
        
        rs.MessageBox("do not use ---> under development")
        self.ID=posno
        self.FileName=posno+".ncw"
        self.WPlane=plane
        self.BBX=bbx
        self.Options=[]
        self.Job=[]
        self.Cut=[]
        self.Bar=[]
        self.Work=[]
    
    def __str__(self):
        string=""
        con=self.Options+self.Job+ self.Bar + self.Cut + self.Work
        for item in con:
            string+=item+"\n"
                    
        return string
        
    def SetOptions(self,oscale=1,ovendorid=2700,osecsurf=3,osecintr=1,osecextr=1):
        
        options=[]
        options.append(":OPTIONS")
        options.append("OScale = " +str(oscale))            #skalierungsfaktor
        options.append("OVendorID = "+str(ovendorid))       #erzeuger id 0=elu 2700 ISD
        options.append("OSecSurf = " +str(osecsurf))        #sicherheitsabstand flaechenueberfahrt
        options.append("OSecIntr = " +str(osecintr))        #sicherheitsabstand tiefe
        options.append("OSecExtr = " +str(osecextr))        #additional run
        self.Options=options
        return options
        
    def SetJob(self,cncdriver="",jno=1,jidentno="",info=""):
        
        job=[]
        job.append(":JOB")
        job.append("cncdriver = ''")                        #version info falls deploys getrackt werden
        job.append("JNo = " + str(jno))                     #job no bei mehreren zuschnitten je ncw datei      
        job.append("JIdentNo ="+str(jidentno))              #auftragsname        
        job.append("Var0 = 0")
        job.append("Var1 = 0")
        job.append("Var2 = 0")
        job.append("Var3 = 0")
        job.append("Var4 = 0")
        job.append("Var5 = 0")
        job.append("Var6 = 0")
        job.append("Var7 = 0")
        job.append("Var8 = 0")
        job.append("Var9 = 0")  
        job.append("info = " + str(info))                   #ergaenzende info 
        self.Job=job
        return job
        
    def SetBar(self,bno,bidentno,blength,bwidth,bheight,bdescription="",bsur="",bcount=1):
        
        bar=[]
        bar.append(":BAR")
        bar.append("BNo = " + str(bno))                     #fortlaufende nummer int
        bar.append("BDescription = " + str(bdescription))   #ergaenzende beschreibung
        bar.append("BIdentNo = " + '"' + str(bidentno)+'"') #name der zugehörigen querschnittsdatei
        bar.append("BSur = "+ str(bsur))                    #angaben zur oberflaeche
        bar.append("BCount = " + str(bcount))               #anzahl bei gleichteilen
        bar.append("BLength = "+ str(blength))              #stablaenge
        bar.append("BWidth = "+ str(bwidth))                #stabbreite
        bar.append("BHeight = "+ str(bheight))              #stabhoehe
        self.Bar=bar
        return bar
        
    def SetCut(self,clength,cno=1,ccount=1,cdescription="",ccomno=0,crotation=0,canglelh=90,canglerh=90,canglelv=90,canglerv=90,cgencuts=1,cgenextr=1.0,cutstart=0.0,cutlossl=0.0,cutLossr=0.0):
        
        cut=[]
        cut.append(":CUT")
        cut.append("CNo = "+str(cno))
        cut.append("CCount = "+str(ccount))             #Anzahl der Stuecke
        cut.append("CDescription = "+str(cdescription)) #Stueckbeschreibung
        cut.append("CComNo = "+str(ccomno))             #Autragsnummer
        cut.append("CPartNo = "+str(self.ID))        #Teilenummer
        cut.append("CRotation = "+str(crotation))       #Orientierung des Stueckes
        cut.append("CAngleLH = " +str(canglelh))        #Winkel in Horizontalebene links
        cut.append("CAngleRH = " +str(canglerh))        #Winkel in Horizontalebene rechts
        cut.append("CAngleLV = " +str(canglelv))        #Winkel in Vertikalebene links
        cut.append("CAngleRV = " +str(canglerv))        #Winkel in Vertikalebene rechts
        cut.append("CLength = " + str(clength))         #Spitzenlaenge des umschliessendem Quaders
        cut.append("CGenCuts = " + str(cgencuts))       #
        cut.append("CGenExtr = " + str(cgenextr))       #
        cut.append("CutStart = " + str(cutstart))       #
        cut.append("CutLossL = " + str(cutlossl))       #
        cut.append("CutLossR = " + str(cutLossr))       #
        self.Cut=cut
        return cut
    
    def AddHole(self,workno,plane,startpoint,endpoint,diameter,dsecint=1,dsecext=1,priority=0,name=""):
        #one chamber drills
        plok=self._lokcoo(startpoint)
        ax,az,side=self._wplanedef(plane)
        d=self._depthtable([startpoint,endpoint])
        
        hole=[]
        hole.append(":WORK")
        hole.append("WNo = "+str(wno))
        hole.append("WType = "+'"'+"D"+'"')
        hole.append("WComment = "+ name)
        hole.append("WSide = " + str(_wside(point)))
        hole.append("WPriority = " + str(priority))
        hole.append("WPTransX = 0.00")
        hole.append("WPTransY = 0.00")
        hole.append("WPTransZ = 0.00")
        
        hole.append("WX1 = " + str(_lokcoo(plok.X)))
        hole.append("WY1 = " + str(_lokcoo(plok.Y)))
        hole.append("WHeight = 0.00") #lage auf bbx
        hole.append("WDepth = " + str(d[1]))#lage des endpunktes im bezug auf die bbx
        hole.append("WW1 = " + str(diameter))
        hole.append("WDT0D = " + str(d[0]))#depth table first startpoint
        hole.append("WDT0M = 0")
        hole.append("WDT0F = 0.00")
        hole.append("WDT1D = " + str(d[1]))#depth table second startpoint/or endpoint
        hole.append("WDT1M = 1")
        hole.append("WDT1F = 1.00")
        hole.append("WDTSecIntr = "+ str(dsecint))
        hole.append("WDTSecExtr = "+ str(dsecext))
        
        self.Work+=hole
        return hole
    
    def AddTap(self,wno):
        tap=[]
        tap.append(":WORK")
        tap.append("WNo = "+str(wno))
        tap.append("WType = "+'"'+"T"+'"')
        tap.append("WSide = " + str(_wside()))
        
        self.Work+=tap
        return tap
    
    def AddEHole(self,wno):
        slot=[]
        slot.append(":WORK")
        slot.append("WNo = "+str(wno))
        slot.append("WType = "+'"'+"LL"+'"')
        slot.append("WSide = "+ str(_wside()))
        
        self.Work=slot
        return slot
    
    def AddRHole(self,wno):
        rect=[]
        rect.append(":WORK")
        rect.append("WNo = "+str(wno))
        rect.append("WType = "+'"'+"R"+'"')
        rect.append("WSide = " + str(_wside()))
        
        self.Work+=rect
        return rect
    
    def AddText(self):
        pass
    
    def AddFreemill(self,wno):
        freemill=[]
        freemill.append(":WORK")
        freemill.append("WNo = "+str(wno))
        freemill.append("WType = "+'"'+"M"+'"')
        freemill.append("WSide = " + str(_wside()))
        
        
        self.Work+=freemill
        return freemill
        
    def AddSaw(self,wno,):
        saw=[]
        saw.append(":WORK")
        saw.append("WNo = "+str(wno))
        saw.append("WType = "+'"'+"S"+'"')
        saw.append("WSide = "+ str(_wside()))

        """
        :WORK
        // Laufende Nummer der Bearbeitung
        WNo = 36
        // Bearbeitungstyp Schnitt
        WType = "S"
        // freie Seite
        WSide = 7
        // Startpunkt auf der freien Seite
        WX1 =   0.00
        WY1 =   0.00
        // Endpunkt auf der freien Seite
        WX2 = -212.51
        WY2 =   0.00
        // eingeschlossener Winkel bei Doppelschnitten
        WAngle =   0.00
        WW1 =  -1.00
        WW2 =   0.00
        WW3 =   0.00
        WW4 =   0.00
        // Seite
        WSide = 7
        // Verschiebungsvektor der freien Seite
        WPTransX = 3846.84
        // Verschiebungsvektor der freien Seite
        WPTransY =   0.00
        // Verschiebungsvektor der freien Seite
        WPTransZ = -120.00
        // Drehwinkel der freien Seite
        WPAngleX =  90.98
        WPAngleZ = -194.58
        """
        self.Work+=saw
        return saw
        
    def _lokcoo(self,point):
        return rs.XformWorldToCPlane(point,self.WPlane)
        
    def _wplanedef(self,planetar):
        
        #die 180° variante berücksichtigen
        planeref=Rhino.Geometry.Plane(plane.Origin,self.WPlane.XAxis,self.WPlane.YAxis)
        
        ref=rs.GetObject("from")
        tar=rs.GetObject("to")
        
        pvref=rs.PolylineVertices(ref)
        pvtar=rs.PolylineVertices(tar)
        
        planeref=rs.PlaneFromPoints(pvref[0],pvref[1],pvref[2])
        planetar=rs.PlaneFromPoints(pvtar[0],pvtar[1],pvtar[2])
        planeref.Origin=planetar.Origin

        #AROUND Z
        i=rs.PlanePlaneIntersection(planeref,planetar)
        
        if i==None:
            aroundx=0.00
            aroundz=0.00
            
        else:
            vint=i[1]-i[0]
            vint.Unitize()
            
            #AROUND Z
            pcvint=rs.XformWorldToCPlane(planeref.Origin+vint*50,planeref)
            aroundz=rs.VectorAngle(planeref.XAxis,vint)
            rs.AddPoint(planeref.Origin+vint*50)
    
            if (pcvint.X<0 and pcvint.Y<0) or (pcvint.Y<0 and pcvint.X>0)  :
                vint*=-1
                aroundz=rs.VectorAngle(planeref.XAxis,vint)
                pcvint=rs.XformWorldToCPlane(planeref.Origin+vint*50,planeref)
            aroundz=(180-aroundz)*-1
            rs.AddLine(planeref.Origin,planeref.Origin+vint*50)
            rs.AddLine(planeref.Origin,planeref.Origin+planeref.XAxis*50)
            
            #AROUND X
            pln=rs.PlaneFromNormal(planetar.Origin,vint)
            iref=rs.PlanePlaneIntersection(planeref,pln)
            vref=iref[1]-iref[0]
            itar=rs.PlanePlaneIntersection(planetar,pln)
            vtar=itar[1]-itar[0]
            pcvtar=rs.XformWorldToCPlane(planeref.Origin+vtar*50,planeref)
            if pcvtar.Z<0:
                vtar*=-1
            
            vtar.Unitize()
            vref.Unitize()
    
            if rs.Distance(planeref.Origin+planeref.XAxis*50,planeref.Origin+vref*50) > rs.Distance(planeref.Origin+planeref.XAxis*50,planeref.Origin-vref*50):
                vref*=-1
            aroundx=rs.VectorAngle(vref,vtar)
            
            #VIZ
            rs.AddLine(planeref.Origin,planeref.Origin+vref*50)
            rs.AddLine(planeref.Origin,planeref.Origin+vtar*50)
            pls=rs.AddPlaneSurface(planeref,50,50)
            pls=rs.RotateObject(rs.CopyObject(pls),planeref.Origin,aroundx,planeref.XAxis)
            rs.RotateObject(rs.CopyObject(pls),planeref.Origin,aroundz,planeref.ZAxis)
        
        return None
        
    def _depthtable(self,points):
        return [0,0]
        

class NCTypes:    

    def __init__(self):
        self.Text="gtext"
        self.Hole="hole"
        self.Thread="thread"
        self.EHole="ehole"
        self.RHole="rhole"
        self.Freemill="freemill"
        self.Saw="saw"
        self.Bolt="bolt"
        self.Silhouette="silhouette"
        self.Help="help"
        self.QSExt="profileqsext"
        self.QSInt="profileqsint"
    
    def ToNCW(self,nctype):
        if nctype==self.Text:
            return None
        elif nctype==self.Hole:
            return '"D"'
        elif nctype==self.Thread:
            return '"T"'
        elif nctype==self.EHole:
            return '"L"'
        elif nctype==self.RHole:
            return '"R"'
        elif nctype==self.Freemill:
            return '"M"'
        elif nctype==self.Saw:
            return '"S"'
        elif nctype==self.Bolt:
            return None
        elif nctype==self.Silhouette:
            return None
        elif nctype==self.Help:
            return None
        else:
            return False
            
            
def AbrufListeFromNCListe():
    for i in range(15,73):
        name="1739-WN3083330-1-5600_Abruf-"+str(i)+"+1mm.csv"
        path=r"G:\BV\1739 - Moynihan Station-New York\06 Zeichnungen\seele (DWG)\BT-F-Train Hall\02 Werkstatt\Fertigungsdaten\NC-Data\\"
        fo=open(path+name)
        lines=[]
        for line in fo:
            if line!="":
                lines.append(line)
        fo.close()
        abrufstring="PARTNAME;QTY;PROFILNAME;BOUNDINGBOX-L;BOUNDINGBOX-B;BOUNDINGBOX-H\r"
        lines.pop(0)
        for line in lines:
            linesplit=line.split(";")
            abrufstring+=linesplit[0]+";1;"+linesplit[1]+";"+linesplit[3]+";"+linesplit[4]+";"+linesplit[5]+"\r"
        
        f=open(path+"\\"+name.replace(".csv","")+"_Abrufliste.csv","w")
        f.write(abrufstring)
        f.close()
    
    
def test_nc():
    #beispiel
    
    obj1=NCCollection("WN100")
    
    item1=NCItem(rs.PlaneFromNormal([0,0,0],[0,0,1]),"C4000-1","WN100",[5000,20,50],True)
    
    item1.AddSaw(rs.PlaneFromNormal([0,0,0],[1,1,0]),"V",0,1,True)
    item1.AddSaw(rs.PlaneFromNormal([1000,0,0],[1000,700,50]),"H",0,0,True)
    item1.AddHole([100,-10,0],[100,-10,-8],"8mm",True)
    item1.AddEHole([200,-20,0],[200,-20,-8],[220,-20,0],"22mm")
    item1.AddRHole([300,-20,0],[300,-20,-8],[320,-20,0],"h=30mm")
    item1.AddText([600,-20,0],[650,-20,0],[600,-20,8],"jaqueline","8mm")
    
    obj1.Add(item1)
    
    item2=NCItem(rs.PlaneFromNormal([0,0,0],[0,0,1]),"C4000-2","WN100",[5000,20,50],True)
    obj1.Add(item2)
    item3=NCItem(rs.PlaneFromNormal([0,0,0],[0,0,1]),"C4000-3","WN100",[5000,20,50],True)
    obj1.Add(item3)
    
    obj1.SplitExportCSV(r"C:\Users\lippert_sebastian.SEELE\Desktop\NeuerOrdner")
    
    
    return 0

if __name__ == '__main__':
   #AbrufListeFromNCListe()
   test_nc()
    


