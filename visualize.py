# -*- encoding: utf-8 -*-
"""
Script written by S. Lippert for Seele GmbH
Version 1.0 as of 2018-05-03
Copyright by Seele GmbH
"""

import rhinoscriptsyntax as rs
import scriptcontext as sc
import System
import sys
import math
import Rhino


def CalcColorValues_OLD(data,cv=0,val=None,mi=None,ma=None):
    """calculates color value based on linear function
    Parameters:
      data= list with all/min/max values to reparameterize value
      cv = critical value -> shift in max/min dir to focus a value range -> RGB[255,255,0]
      val = the value the color to be calculated for if None all values in data are calculated
    Returns:
        list of three integers -> RGB Color values
    """
    
    if mi==None:
        mi=min(data)
    if ma==None:
        ma=max(data)
    
    if mi==0:
        mi=0.001
    
    mid=mi+(ma-mi)/2
    if cv<mi:
        cv=mid
    
    s1=255/(cv-mi)
    s2=-255/(ma-cv)
    b1=-s1*mi+0
    b2=-s2*ma+0
    
    if val!=None:
        col=None
        if val<cv:
            col=[int(s1*val+b1),255,0]
        else:
            col=[255,int(s2*val+b2),0]
    else:
        col=[]
        for val in data:
            if val<cv:
                col.append([int(s1*val+b1),255,0])
            else:
                col.append([255,int(s2*val+b2),0])
    return col

def CalcColorValues(data,cv=0,val=None,mi=None,ma=None):
    """calculates color value based on linear function
    Parameters:
      data= list with all/min/max values to reparameterize value
      cv = critical value -> shift in max/min dir to focus a value range -> RGB[255,255,0]
      val = the value the color to be calculated for if None all values in data are calculated
    Returns:
        list of three integers -> RGB Color values
    """
    
    if mi==None:
        mi=min(data)
    if ma==None:
        ma=max(data)
    
    if mi==0:
        mi=0.001
    
    mid=mi+(ma-mi)/2
    if cv<mi:
        cv=mid
    
    s1=255/(cv-mi)
    s2=-255/(ma-cv)
    b1=-s1*mi+0
    b2=-s2*ma+0
    
    if val!=None:
        col=None
        if val<cv:
            col=[int(s1*val+b1),255,0]
        else:
            col=[255,int(s2*val+b2),0]
        for k in range(3):
            if col[k]<0:
                col[k]=0
    else:
        col=[]
        for val in data:
            if val<cv:
                col.append([int(s1*val+b1),255,0])
            else:
                col.append([255,int(s2*val+b2),0])
    return col

def AddColorScala(data,cv=0,sizex=50,sizey=400,txtheight=3.5,title="",mi=None,ma=None):
    
    if ma==None:
        ma=max(data)
    if mi==None:
        mi=min(data)
    
    mid=mi+(ma-mi)/2
    if cv<mi:
        cv=mid
    
    rs.AddLayer("rgb-scala")
    
    a=[0,255,0]
    b=[255,255,0]
    c=[255,0,0]

    
    fak=(cv-mi)/(ma-mi)
    sizecv=fak*sizey
    
	
    vx=[[0,0,0],[sizex,0,0],[sizex,sizecv,0],[0,sizecv,0],[sizex,sizey,0],[0,sizey,0]]
    fc=[[0,1,2,3],[3,2,4,5]]
    col=[a,a,b,b,c,c]
    
    obj=[]
    obj.append(rs.AddMesh(vx,fc, vertex_colors=col))
    obj.append(rs.AddText(str(mi),vx[1],txtheight))
    obj.append(rs.AddText(str(cv),vx[2],txtheight))
    obj.append(rs.AddText(str(ma),vx[4],txtheight))
    if title!="":
        obj.append(rs.AddText(title,[0,-txtheight*3,0],txtheight*2))
    
    rs.ObjectLayer(obj,"rgb-scala")
    
    return obj
    
def AddHistogram(data,step=5,sizex=100,sizey=400,txtsize=10,data2=None,dataunit="mm",data2unit="lfm"):
    
    rs.AddLayer("histo")
    
    mi=min(data)
    ma=max(data)
    
    cn=int((ma-mi)/step)+1
    step=(ma-mi)/cn
    histo=[]
    adddata=[]
    
    for i in range(0,cn+1):
        histo.append(0)
        adddata.append(0)
        for j in range(0,len(data)):
            if data[j]!=None:
                if data[j]<=mi+i*step:
                    histo[i]+=1
                    adddata[i]+=data2[i]
                    data[j]=None
                    
    #skalieren
    pt=[]
    faky=sizey/cn
    fakx=sizex/max(histo)
    for i in range(0,cn+1):
        #pt.append([histo[i]*-fakx,faky*i,0])
        if histo[i]>0:
            line=rs.AddLine([0,faky*i,0],[histo[i]*-fakx,faky*i,0])
            rs.ObjectLayer(line,"histo")
            txt=rs.AddText(str(histo[i])+ "pcs \r"+ str(adddata[i])+ data2unit,[histo[i]*-fakx-txtsize*(len(str(histo[i]))+len(dataunit)),faky*i,0],txtsize)
            rs.ObjectLayer(txt,"histo")
            txt=rs.AddText(str(round(mi+i*step,1))+dataunit,[0,faky*i,0],txtsize)
            rs.ObjectLayer(txt,"histo")
            
    return histo

class Color:
    
    def __init__(self,count=10):
        self.R=255
        self.G=0
        self.B=255
        self.Range=self.__build_range()
        self.Step=int(len(self.Range)/(count-1))
        self.ID=0
        
    def __build_range(self,step=1):
        
        ranger=[]
        phase=0
        while phase<5:
            if phase==0:
                if self.R>step:
                    self.R-=step
                else:
                    phase+=1
                self.G=0
                self.B=255
                
            if phase==1:
                if self.G<255-step:
                    self.G+=step
                else:
                    phase+=1
                self.R=0
                self.B=255
            
            if phase==2:
                if self.B>step:
                    self.B-=step
                else:
                    phase+=1
                self.R=0
                self.G=255
            
            if phase==3:
                if self.R<255-step:
                    self.R+=step
                else:
                    phase+=1
                self.G=255
                self.B=0
            
            if phase==4:
                if self.G>step:
                    self.G-=step
                else:
                    phase+=1
                self.R=255
                self.B=0
        
            ranger.append([self.R,self.G,self.B])
        return ranger
    
    def __call__(self):
        if self.ID>len(self.Range):
            return [255,255,255]
        val=self.Range[self.ID]
        self.ID+=self.Step
        return val

class SeeleMaterials:
    
    def __init__(self):

        #loggin.info("@SeeleMaterials.__init__()")

        self.AL=[[52,125,248],0.,2700.,-1]
        self.MS=[[221,125,150],0.,8000.,-1]
        self.VA=[[206,74,78],0.,7900.,-1]
        self.BRASS=[[140,100,4],0.,8900.,-1]

        self.SILIKON=[[136,23,77],0.,1500.,-1]
        self.EPDM=[[233,39,78],0.,1400.,-1]
        self.SGP=[[169,38,5],0.5,1500.,-1]
        self.PVB=[[169,38,5],0.5,1500.,-1]
        self.PTFE=[[255,176,70],0.,2200.,-1]
        self.PE=[[255,176,70],0.,950.,-1]
        self.PVC=[[169,38,5],0.5,1400.,-1]
        
        self.WOOD=[[153,114,76],0.,600.,-1]
        self.PURENIT=[[171,66,3],0.,500.,-1]
        self.GL=[[155,224,12],0.5,2500.,-1]
        self.CONCRETE=[[170,170,170],0.,2600.,-1]
        
        self.VM=[[170,193,2],0.,8000.,-1]
        self.INSULATION=[[251,175,0],0.,150.,-1]
        self.GROUTING=[[236,231,26],0.,2600.,-1]
        self.FOIL=[[145,15,40],0.,1500.,-1]
        self.PLASTIC=[[255,176,70],0.,1500.,-1]

        
        for key in self.__dict__.keys():            
            self.__dict__[key][3]=self.Add(key,self.__dict__[key][0],self.__dict__[key][1])
              
    def __str__(self):
        return "\n".join(self.__dict__)

    def Add(self,key,color,opacity):

        id=sc.doc.Materials.Find(key,True)
        if id==-1:
            id=sc.doc.Materials.Add()
        else:
            return id

        mat = sc.doc.Materials[id]
        mat.Name=key
        mat.DiffuseColor = System.Drawing.Color.FromArgb(color[0],color[1],color[2])
        mat.Transparency=opacity
        mat.CommitChanges()

        return id

    def AddSome(self,count=10):

        ids=[]
        colors=[]
        col=Color(count)
        for i in range(count):
            c=col()
            key=str(i)
            ids.append(self.Add(key,c,0.))
            colors.append(c)

        return zip(ids,colors)

    def Contains(self,key):
        if key in self.__dict__.keys():
            return True
        return False

    def GetMatID(self,key):
        if self.Contains(key):
            return self.__dict__[key][3]
        return -1

    def GetColor(self,key):
        if self.Contains(key):
            return self.__dict__[key][0]
        return [0.,0.,0.]

    def GetOpacity(self,key):
        if self.Contains(key):
            return self.__dict__[key][1]
        return 1.

    def GetDensity(self,key):
        if self.Contains(key):
            return self.__dict__[key][2]
        return 1.

    def GetDic(self):

        #loggin.info("@SeeleMaterials.GetDic()")

        return self.__dict__



def test():
	color=Color(20)
	for i in range(10):
		col=color()

if __name__=="__main__":
	test()
        