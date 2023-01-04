# -*- encoding: utf-8 -*-
"""
Script written by S. Lippert for Seele GmbH
Copyright by Seele GmbH

2019-10-21 Update slp::     no comments

2020-02-26 Update slp::     1.  Feature().GenNCBreps() method - NCFeatures don't get a brep associated by initilisation
                                Brep(s) are generated on demand by part.ApplyFeature() method. Breps are not stored as a property
                            2.  Part().ApplyFeature() method has been stripped. solid face orientation issues to be resolved (discussion mse)

2020-06-10 Update slp::     1.  Attrib Extension & Simplification
"""

"""
NOTE
#for loggin (VS CODE only) 
#add loc below on top of your application module
import loggin
loggin.basicConfig(filename=sys.path[0]+r"\baseobjects_debug.log",level=#loggin.DEBUG,filemode='w')
#sys.path[0] should be your local %temp% diretory
"""

import sys
import json
import System
import copy
import math
import os
import copy 

#from enum import Enum
#import loggin

import Rhino
import rhinoscriptsyntax as rs  #calls eleminieren
import scriptcontext as sc

globalpath=r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\seele.Rhino.Common"
sys.path.append(globalpath)
from unroll import SheetUnroller,SheetMarker
from ncdata import NCCollection,NCItem,NCTypes,NCWItem
from signature import Text3D
from visualize import Color

PATH_FEATURE_MAP="{}\{}".format(globalpath,"feature_map.json")
PATH_ATTRIB_MAP="{}\{}".format(globalpath,"attrib_map.json")
PATH_VORLAGE_MAP="{}\{}".format(globalpath,"vorlageartikel.json")
PATH_FINISH_MAP="{}\{}".format(globalpath,"finish_map_template.json")
PATH_MATERIAL_MAP="{}\{}".format(globalpath,"material_map.csv")



#class NCCollection
#class 


class ThreadHoleDiameters:
    
    M1=0.75
    M2=1.6
    M3=2.5
    M4=3.3
    M5=4.2
    M6=5.0
    M8=6.8
    M10=8.5
    M12=10.2
    M16=14.0
    M20=17.5
    M24=21.0
    M30=26.5
    M36=32.0
    M42=37.5
    M48=43.0
    M56=50.5
    M64=58.0


class SeeleColors:
    
    def __init__(self):

        #loggin.info("@SeeleColors.__init__()")

        self.Dic={
        "AL":[52,125,248],
        "MS":[221,125,150],
        "VA":[206,74,78],
        "PE":[255,176,70],
        "GL":[155,224,12],
        "SGP":[169,38,5], #PVC
        "PVB":[169,38,5], #PVC
        "PURENIT":[171,66,3],
        "SILIKON":[136,23,77],
        "EPDM":[233,39,78],
        "VM":[170,193,2]}
        
    def __call__(self,string):

        #loggin.info("@SeeleColors.__call__()")

        if string in self.Dic.keys():
            return self.Dic[string]
        else:
            return [0,0,0]

    def Contains(self,key):
        if key in self.Dic.keys():
            return True
        return False


class SeeleMaterials:
    
    def __init__(self,createSeeleMaterials=True):

        #loggin.info("@SeeleMaterials.__init__()")
        if createSeeleMaterials:
            self.Dic={
            "AL":([52,125,248],0.0,2700.),
            "MS":([221,125,150],0.0,8000.),
            "VA":([206,74,78],0.0,8500.),
            "PE":([255,176,70],0.0,1000.),
            "GL":([155,224,12],0.5,2500.),
            "SGP":([169,38,5],0.5,1500.), #PVC
            "PVB":([169,38,5],0.5,1500.), #PVC
            "PURENIT":([171,66,3],0.0,500.),
            "SILIKON":([136,23,77],0.0,1500.),
            "EPDM":([233,39,78],0.0,1500.),
            "VM":([170,193,2],0.0,8000.)}            

            for key in self.Dic.keys():            
                self.Dic[key]=[self.Add(key,self.Dic[key][0],self.Dic[key][1]),self.Dic[key][2]]
        
    def GetDic(self):

        #loggin.info("@SeeleMaterials.GetDic()")

        return self.Dic

    def Add(self,key,color,opacity):

        id=sc.doc.Materials.Find(key,True)
        if id==-1:
            id=sc.doc.Materials.Add()
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

    def __call__(self,string,ro=False):

        #loggin.info("@SeeleMaterials.__call__()")

        if string in self.Dic.keys():
            if ro:
                return self.Dic[string][0],self.Dic[string][1]
            else:
                return self.Dic[string][0]
        else:
            return 0
            
            
class SaveAsciFile:
    
    def __init__(self,string,filename):

        #loggin.info("@SaveAsciFile.__init__()")

        with open(filename,'w') as f:
            f.write(string)
            f.close()
        return True


class Export():
    
    def __init__(self,obj=None,filename="",path="",format="",deleteblock=False):

        #loggin.info("@Export.__init__()")

        if path=="":
            path=os.environ['USERPROFILE']+"\\Desktop\\"
        if filename=="":
            filename=strftime("%Y-%m-%d_%H-%M-%S", gmtime())        
        self.Path=path+filename+"."+format
        
        if obj!=None:
            
            rs.SelectObjects(obj)
            rs.Command("-_export " + self.Path + " _enter ")
            rs.UnselectAllObjects()
        
        if deleteblock:
            bln=rs.BlockInstanceName(obj)
            rs.DeleteObject(obj)
            self.KillBlocksRekursiv(bln)
   
    def KillBlocksRekursiv(self,bln):

        #loggin.info("@Export.KillBlocksRekursiv()")

        objs=rs.BlockObjects(bln)
        rs.DeleteBlock(bln)
        for obj in objs:
            if rs.IsBlockInstance(obj):
                bln=rs.BlockInstanceName(obj)
                if rs.IsBlock(bln):
                    self.KillBlocksRekursiv(bln)


class File:
    
    def __init__(self,path,attrib=None,feature=None):

        #loggin.info("@File.__init__()")

        self.Path=path
        if attrib==None:
            self.Attrib=Attrib()
        else:
            self.Attrib=attrib
        if feature==None:
            self.Feature=Feature()
        else:
            self.Feature=feature

            
class UnitFactor:
    
    def __init__(self,modelunitsystem=Rhino.UnitSystem.Millimeters):
        
        #loggin.info("@UnitFactor.__init__()")

        self.Factor=1
        if modelunitsystem==Rhino.UnitSystem.Millimeters:
            self.Factor=1.0/1000.0
        elif modelunitsystem==Rhino.UnitSystem.Centimeters:
            self.Factor=1.0/100.0
        elif modelunitsystem==Rhino.UnitSystem.Feet:
            self.Factor=0.0254
        elif modelunitsystem==Rhino.UnitSystem.Inches:
            self.Factor=0.3048
        else:
            print "no UnitSystem Unit linked"
            
            
class Archive(object):
    
    def ToDic(self):

        #loggin.info("@Archive.ToDic()")

        return self.__dict__.copy()
    
    def FromDic(self,dic):        
        
        #loggin.info("@Archive.FromDic()")
        #for key in dic:
        #    self.__dict__[key]=dic[key]
        #return self
        
        return dic
    
    def ToJSON(self,jsonpath,dic=None,savebreps=False,context=None):

        #loggin.info("@Archive.ToJSON()")
        if dic!=None:
            if isinstance(dic,dict):
                with open(jsonpath,'w') as f:
                    f.write(json.dumps(dic,ensure_ascii=True,encoding="utf-8",))
        else:
            with open(jsonpath,'w') as f:
                f.write(json.dumps(self.ToDic(),ensure_ascii=True,encoding="utf-8",))
        
        
        return True

    def FromJSON(self,jsonpath):     
        
        #loggin.info("@Archive.FromJSON()")
        with open(jsonpath,'r') as f:
            return self.FromDic(json.load(f))
        
    def WriteObjAttrib(self,guid,dic):

        obj=sc.doc.Objects.Find(guid)

        for key in dic:
            value=dic[key]
            if not isinstance(value,str):
                #if isinstance(value,float):
                #    value=round(value,1)
                value=str(value)
            obj.Attributes.SetUserString(key,value)
            obj.CommitChanges()

        pass


class APArtikel(Archive):
    
    def __init__(self,lfdnr=0,struktur=0,artikel="",vorlageartikel="",name="",name2="",menge="",mengepmng="",me="",vbme="",laenge=0,breite=0,hoehe=0,staerke=0,flaeche=0,gewicht=0,flaecheme="",material="",zeichnung="",zeichnungpos="",ztext="",herststueli="",einkauf="",fertigung="",auftrag="",lager="",beistellung="",fremdmontage="",finishcode="",matcode="",rawmat="",unrolx=0,unroly=0,unrolz=0):
        
        #loggin.info("@APArtikel.__init__()")

        self.Error=""
        self.Children=[]
        self.VBME=vbme

        self.LFDNR=lfdnr
        self.Struktur=struktur
        self.Artikel=artikel
        self.Vorlageartikel=vorlageartikel
        self.Name=name
        self.Name2=name2
        self.Menge=menge
        self.MengePMng=mengepmng
        self.ME=me
        self.Laenge=laenge
        self.Breite=breite
        self.Hoehe=hoehe
        self.Staerke=staerke
        self.Gewicht=gewicht
        self.FlaecheME=flaecheme
        self.Material=material
        self.Zeichnung=zeichnung
        self.ZeichnungPos=zeichnungpos
        self.ZText=ztext
        self.HerstStueli=herststueli
        self.Einkauf=einkauf
        self.Fertigung=fertigung
        self.Auftrag=auftrag
        self.Lager=lager
        self.Beistellung=beistellung
        self.Fremdmontage=fremdmontage
        
        self.FinishCode=finishcode
        self.MatCode=matcode
        self.RawMat=rawmat
        self.UnrolX=unrolx
        self.UnrolY=unroly
        self.UnrolZ=unrolz
    
    def Copy(self,strukturplus=0):
        
        #loggin.info("@APArtikel.Copy()")

        copy=APArtikel()
        
        copy.Error=self.Error
        copy.Children=[]
        copy.VBME=self.VBME

        copy.LFDNR=self.LFDNR
        copy.Struktur=self.Struktur+strukturplus
        copy.Artikel=self.Artikel
        copy.Vorlageartikel=self.Vorlageartikel
        copy.Name=self.Name
        copy.Name2=self.Name2
        copy.Menge=self.Menge
        copy.MengePMng=self.MengePMng
        copy.ME=self.ME
        copy.Laenge=self.Laenge
        copy.Breite=self.Breite
        copy.Hoehe=self.Hoehe
        copy.Staerke=self.Staerke
        copy.Gewicht=self.Gewicht
        copy.FlaecheME=self.FlaecheME
        copy.Material=self.Material
        copy.Zeichnung=self.Zeichnung
        copy.ZeichnungPos=self.ZeichnungPos
        copy.ZText=self.ZText
        copy.HerstStueli=self.HerstStueli
        copy.Einkauf=self.Einkauf
        copy.Fertigung=self.Fertigung
        copy.Auftrag=self.Auftrag
        copy.Lager=self.Lager
        copy.Beistellung=self.Beistellung
        copy.Fremdmontage=self.Fremdmontage
        
        copy.FinishCode=self.FinishCode
        copy.MatCode=self.MatCode
        copy.RawMat=self.RawMat
        copy.UnrolX=self.UnrolX
        copy.UnrolY=self.UnrolY
        copy.UnrolZ=self.UnrolZ
        
        return copy
        
    def Update(self):
        
        #loggin.info("@APArtikel.Update()")

        self.Name=self.GetVAName(self.Artikel)
        #if self.RawMat!="":
        if self.RawMat=="xxx":
            if self.VBME=="m2":
                child=APArtikel()
                child.Struktur=self.Struktur+1
                child.Artikel=self.RawMat
                child.Menge=(self.UnrolX*self.UnrolY)/1000**2
                child.ME=self.VBME
                child.Laenge=self.UnrolX
                child.Breite=self.UnrolY
                child.Hoehe=self.UnrolZ
                child.Gewicht=self.Gewicht
                self.Children.append(child)
            elif self.VBME=="m":
                me="m"
                if isinstance(self.Laenge,int):
                    self.Laenge=float(self.Laenge)
                menge=self.Laenge/1000
                pro=""
                #syntax: rawmat="1745-WN3083820-5700?5700/6"
                if "?" in self.RawMat:
                    spl=self.RawMat.split("?")
                    self.RawMat=spl[0]
                    #print spl[0]
                    spl=spl[len(spl)-1].split("/")
                    rawlength=float(spl[0])
                    #print rawlength
                    pro=float(spl[1])
                    #print pro
                    step=rawlength/pro
                    #print step
                    cn=1
                    for i in range(1,int(pro)):
                        if self.Laenge>step*i:
                            cn+=1
                    #print "schs gonna looklike: menge: "+str(cn)+" pro: "+str(int(pro)) + " me: " + "Stück"  
                    pro=str(int(pro))
                    menge=cn
                    me="Stück"
                    
                child=APArtikel()
                child.Struktur=self.Struktur+1
                child.Artikel=self.RawMat
                child.Menge=menge
                child.MengePMng=pro
                child.ME=me
                child.Laenge=self.Laenge
                child.Gewicht=self.Gewicht
                self.Children.append(child)
            """
            elif self.VBME=="m":
                child=APArtikel()
                child.Struktur=self.Struktur+1
                child.Artikel=self.RawMat
                child.Menge=self.Laenge/1000
                child.ME=self.VBME
                child.Laenge=self.Laenge
                child.Gewicht=self.Gewicht
                self.Children.append(child)
            """
            
    def __str__(self):
        
        #loggin.info("@APArtikel.__str__()")

        self.Update()
        
        if self.Artikel=="stuelikopf":
            string=""
            string+="XXZ.-Pos.          : \n"  
            string+="Artkel-Nr.      : S-\n"
            string+="Benennung        : \n"
            string+="Benennung 2      : \n"
            string+="ME               : \n"
            string+="Laenge           : \n"
            string+="Breite           : \n"
            string+="Hoehe            : \n"
            string+="Abmessung        : \n"
            string+="kg/ME            : \n"
            string+="Unit/Site        : \n"
            string+="Zusatztext       : " + self.Name2 + "\n"
            string+="Freigabestatus   : \n"
            string+="HEL_SACHNUMMER   : \n"
            string+="Materialcode     : \n"
            string+="Oberflaechencode : \n"
            string+="\n" 
            string+="Stufe;Menge;Artikel-Nr.;Benennung;Benennung 2;pro;ME;Länge;Breite;Höhe;Abmessung;kg/ME;Z.-Pos.;E;F;A;L;B;M;Unit/Site;Zusatztext;Freigabestatus;Blechdicke;Blechzuschnitt L;Blechzuschnitt B;Materialcode;Oberflaechencode;Halbzeugnummer;Halbzeugname;\n"
        else:
            string=""
            string+=str(self.Struktur) + ";"
            if isinstance(self.Menge,float):
                self.Menge=round(self.Menge,3)
            string+=str(self.Menge)+";"
            string+=self.Artikel+";"
            string+=self.Name+";"
            string+=";"
            string+=self.MengePMng + ";"
            string+=self.ME+";"
            string+=str(round(self.Laenge,0))+";"
            string+=str(round(self.Breite,0))+";"
            string+=str(round(self.Hoehe,0))+";"
            string+=";"
            string+=str(round(self.Gewicht,2))+";"
            string+=self.ZeichnungPos+";"
            string+=self.Einkauf+";"
            string+=self.Fertigung+";"
            string+=self.Auftrag+";"
            string+=self.Lager+";"
            string+=";"
            string+=";"
            string+=";"
            string+=self.Name2+";"
            string+=";"
            string+=";"
            string+=";"
            string+=";"
            string+=self.MatCode+";"
            string+=self.FinishCode+";"
            string+=self.RawMat+";"
            string+=";\n"
        
        for child in self.Children:
            string+=str(child)+""
        
        return string#.replace(".",",")
    
    def GetVAName(self,va):
        
        #loggin.info("@APArtikel.GetVAName()")

        f=open(globalpath+"\\vorlageartikel.json",'r')
        x=json.loads(f.read())
        f.close()
        if va in x:
            return eval(x[va])
        else: 
            return ""
        
    def FromDic(self,dic):
        
        #loggin.info("@APArtikel.FromDic()")

        if dic["TYP"]=="Part":
            obj=Part().FromDic(dic)
        elif dic["TYP"]=="Profile":
            obj=Profile().FromDic(dic)
        elif dic["TYP"]=="Sheet":
            obj=Sheet().FromDic(dic)
        elif dic["TYP"]=="Product":
            obj=Product().FromDic(dic)
        
        self.Children.append(obj.ToAPArtikel())
        
        return self
        
        
class Attrib(Archive):
    
    def __init__(self,
                    id="",
                    prefix="",
                    zusatztext="",
                    rawmat="",
                    fincode="00",
                    matcode="000",
                    apvorlageno="- keine AP+ Anlage -",
                    einkauf="",
                    fertigung="X",
                    auftrag="X",
                    lager="",
                    vbme="m",
                    textpos=False,
                    menge=1,
                    job="no-job-defined",
                    block=False,
                    subasm="",
                    code="-",
                    location="-",
                    walltype="-",
                    extrusioncompany="-",
                    alloytemper="-",
                    manufacturer="-",
                    glassbuildup="-",
                    uvalue="-",
                    accousticvalue="-"):
        
        #loggin.info("@Attrib.__init__()")

        self.Error=""
        self.ID=id
        self.Prefix=prefix	
        self.ZusatzText=zusatztext
        self.RawMat=rawmat
        self.FinishCode=fincode
        self.MatCode=matcode
        self.APVorlage=apvorlageno
        self.Einkauf=einkauf
        self.Fertigung=fertigung
        self.Auftrag=auftrag
        self.Lager=lager
        self.VBME=vbme
        self.TextPos=textpos
        self.Menge=menge
        self.Job=job
        self.Block=block
        self.SubASM=subasm
        self.Name=None 
        self.Code=code
        self.Location=location
        self.Walltype=walltype
        self.ExtrusionCompany=extrusioncompany
        self.AlloyTemper=alloytemper
        self.Manufacturer=manufacturer
        self.GlassBuildUp=glassbuildup
        self.UValue=uvalue
        self.AccousticValue=accousticvalue

        #generated via mapping on the fly
        self.APText=""
        self.FinishText=""
        self.MaterialText=""
        self.Name=""
        self.DieNumber=""
        
    def __str__(self):
        
        #loggin.info("@Attrib.__str__()")

        for key in self.__dict__:
            string+="{}: {}\n".format(key.ljust(20),self.__dict__[key])
        
        return string
    
    def __call__(self,
                    id="",
                    prefix="",
                    zusatztext="",
                    rawmat="",
                    fincode="00",
                    matcode="000",
                    apvorlageno="- keine AP+ Anlage -",
                    einkauf="",
                    fertigung="X",
                    auftrag="X",
                    lager="",
                    vbme="m",
                    textpos=False,
                    menge=1,
                    job="no-job-defined",
                    block=False,
                    subasm="",
                    code="-",
                    location="-",
                    walltype="-",
                    extrusioncompany="-",
                    alloytemper="-",
                    manufacturer="-",
                    glassbuildup="-",
                    uvalue="-",
                    accousticvalue="-"):
        
        new_attrib=Attrib(id,prefix,zusatztext,rawmat,fincode,matcode,apvorlageno,einkauf,fertigung,auftrag,lager,vbme,textpos,menge,job,block,subasm,
                            code,location,walltype,extrusioncompany,alloytemper,manufacturer,glassbuildup,uvalue,accousticvalue)
        def_attrib=Attrib()
        for key in self.__dict__:
            if key in new_attrib.__dict__: 
                val_new=new_attrib.__dict__[key]
                val_default=def_attrib.__dict__[key]
                
                if val_new == val_default:
                    new_attrib.__dict__[key]=self.__dict__[key]            #copy.copy(self.__dict__[key].copy())
            else:
                new_attrib.__dict__[key]=self.__dict__[key]                #copy.copy(self.__dict__[key])

        #new_attrib.APText=self.MapJSON(new_attrib.APVorlage,PATH_VORLAGE_MAP)
        #new_attrib.FinishText=self.MapJSON(new_attrib.FinishCode,new_attrib.PathFinMap)
        #new_attrib.MaterialText=self.MapCSV(new_attrib.MatCode,PATH_MATERIAL_MAP,2)
        
        new_attrib.__dict__=new_attrib.__dict__.copy()

        return new_attrib

    def PosNo(self):

        #loggin.info("@Attrib.PosNo()")

        if self.ID=="" or self.Prefix=="":
            if self.ID=="":
                return self.Prefix
            elif self.Prefix=="":
                return self.ID
            else:
                return "!!None!!"
        else:
            return self.Prefix + "-" + self.ID
    
    def MapJSON(self,key,path):
        dic=Archive().FromJSON(path)
        if key in dic:
            return dic[key]
        return ""

    def MapCSV(self,key,path,index):
        with open(path,'r') as f:
            for line in f:
                spl=line.split(";")
                if key==spl[0]:
                    if len(spl)>index:
                        return spl[index]
        return ""                 

    def GetWN(self):
        if "WN" in self.RawMat:
            wn=[x for x in self.RawMat.split("-") if "WN" in x]
            if len(wn)>0:
                return wn[0]
        else:
            return "-"

    def Copy(self):
        
        #loggin.info("@Attrib.Copy()")

        newattrib=Attrib()
        for key in self.__dict__:
            newattrib.__dict__[key]=self.__dict__[key]
        
        return newattrib
    
    def ToDic(self):

        #loggin.info("@Attrib.ToDic()")
        
        dic=self.__dict__.copy()
        dic.update({"TYP":"Attrib"})
        return dic
        
    def ToDic2(self,path_key_map="",path_fin_map=""):        
        #used for writing attributes
        #loggin.info("@Attrib.ToDic2()")
        
        if path_fin_map=="":
            path_fin_map=PATH_FINISH_MAP
        
        self.APText=self.MapJSON(self.APVorlage,PATH_VORLAGE_MAP)
        self.FinishText=self.MapJSON(self.FinishCode,path_fin_map)
        self.MaterialText=self.MapCSV(self.MatCode,PATH_MATERIAL_MAP,2)
        self.Name=self.PosNo()
        self.DieNumber=self.GetWN()

        if path_key_map=="":
            path_key_map=PATH_ATTRIB_MAP
        
        mapkey=Archive().FromJSON(path_key_map)
               
        dic={}

        for key in self.__dict__: 
            val= self.__dict__[key]
            if key in mapkey:
                dic[mapkey[key]]=val
        
        return dic

    def FromDic(self,dic):
        
        #loggin.info("@Attrib.FromDic()")

        for key in dic:
            if dic[key]=="None":
                dic[key]=None
        
        if dic["TYP"]=="Attrib":
            for key in dic:
                self.__dict__[key]=dic[key]
        
        return self

    def Add(self,dic):
        for key in dic:
            self.__dict__[key]=dic[key]
        
        return self
            
###hier reworks noetig ---> einfacher GUID(?) + Geometry (incl. Abfragen)###
class Feature(Archive):
    
    def __init__(self,name="",create=True,file=None,objectid=None,brep=None,text="",layer="",weight=0.,radius=5.,axis=None,angle=None,spacing=(50.,200.,50.),reverse=False,shrink=0.,plane=None,ro=0.,sizex=0.,sizey=0.,sizez=0.,unrolx=0.,unroly=0.,unrolz=0.,nccreate=True,nctype=None,ncnachlauf=0.,nccutspace=0.,ncdiameter=0.,ncshiftx=0.,ncshifty=0.,ncxycut=0.,ncshiftz=0.,notes="",curve=None,lod=0,color=None,rhinomat=None,blockname=None,mat=""):
        
        #loggin.info("@Feature.__init__()")

        self.Error=""
        self.Name=name
        self.Create=create
        self.File=file
        self.ObjectID=objectid
        self.Brep=brep #rename in geometry - sind ja nicht nur breps!!!
        self.BlockName=blockname
        self.Curve=curve
        self.Text=text
        self.Layer=layer        
        self.Justification=Rhino.Geometry.TextJustification.BottomLeft #brauche ich das wirklich??
        self.LOD=lod
        self.Color=color            
        self.RhinoMat=rhinomat
        self.Ro=ro  

        if mat!="":
            if SeeleColors().Contains(mat):
                col_=SeeleColors()(mat)
                mat_,ro_=SeeleMaterials()(mat,ro=True)
                self.Color=col_          
                self.RhinoMat=mat_
                self.Ro=ro_

        self.SaveBrep=False
        if sizex==0.:
            self.Axis=Rhino.Geometry.Line(Rhino.Geometry.Point3d(0,0,0),Rhino.Geometry.Point3d(1000,0,0))
        else:
            self.Axis=Rhino.Geometry.Line(Rhino.Geometry.Point3d(0,0,0),Rhino.Geometry.Point3d(sizex,0,0))
        if axis!=None:
            if isinstance(axis,System.Guid):
                axis=rs.coercegeometry(axis)
            if isinstance(axis,Rhino.Geometry.Line):
                self.Axis=axis
            if isinstance(axis,Rhino.Geometry.LineCurve):
                self.Axis=axis.Line
            if isinstance(axis,Rhino.Geometry.PolylineCurve):
                self.Axis=Rhino.Geometry.Line(axis.PointAtStart,axis.PointAtEnd)
                
        self.Angle=angle
        self.Spacing=spacing
        self.Reverse=reverse
        self.Shrink=shrink
        
        if plane==None:
            self.Plane=Rhino.Geometry.Plane(self.Axis.From,self.Axis.Direction,Rhino.Geometry.Vector3d.CrossProduct(self.Axis.Direction,Rhino.Geometry.Vector3d.ZAxis*-1))    
        else:
            self.Plane=Rhino.Geometry.Plane(plane)
        
        self.Weight=weight
        self.SizeX=sizex
        self.SizeY=sizey
        self.SizeZ=sizez
        self.UnrolX=unrolx
        self.UnrolY=unroly
        self.UnrolZ=unrolz
        self.Radius=radius
        
        self.NCCreate=nccreate
        self.NCType=nctype
        self.NCNachlauf=ncnachlauf
        self.NCCutSpace=nccutspace
        self.NCDiameter=ncdiameter
        self.NCShiftX=ncshiftx
        self.NCShiftY=ncshifty
        self.NCShiftZ=ncshiftz
        self.NCXYCut=ncxycut
        
        self.Notes=notes
        self.Area=0.
        self.Dimension=""

        #self.__BrepFactory()
        
        if self.ObjectID!=None:
            if self.Layer!="":
                rs.AddLayer(self.Layer)
                rs.ObjectLayer(self.ObjectID,self.Layer)
            rs.ObjectName(self.ObjectID,self.Name)
        
    def GenNCBreps(self):
        
        #loggin.info("@Feature.GenNCBreps()")

        if self.Create:
            if self.NCType==NCTypes().Text and self.Text!="":
                if self.SizeY==0:self.SizeY=10
                brep=FeatureFactory().Text(self.Text,size_y=self.SizeY,size_z=self.SizeZ,plane=self.Plane) 
                if brep!=None:   
                    [x.Faces.SplitKinkyFaces(Rhino.RhinoMath.DefaultAngleTolerance, True) for x in brep]
                self.NCShiftY+= self.SizeY*.5
                return brep

            elif self.NCType==NCTypes().Hole:
                brep=FeatureFactory().Hole(diameter=self.SizeX,size_z=self.SizeZ,plane=self.Plane)
                brep.Faces.SplitKinkyFaces(Rhino.RhinoMath.DefaultAngleTolerance, True)
                self.NCDiameter=self.SizeX
                return [brep]
                
            elif self.NCType==NCTypes().EHole:
                brep=FeatureFactory().EHole(size_x=self.SizeX,diameter=self.SizeY,size_z=self.SizeZ,plane=self.Plane)
                brep.Faces.SplitKinkyFaces(Rhino.RhinoMath.DefaultAngleTolerance, True)
                self.NCShiftX=self.SizeX*-1/2
                self.NCDiameter=self.SizeY
                return [brep]

            elif self.NCType==NCTypes().RHole:
                brep=FeatureFactory().RHole(size_x=self.SizeX,size_y=self.SizeY,size_z=self.SizeZ,cornerradius=self.Radius,plane=self.Plane)
                brep.Faces.SplitKinkyFaces(Rhino.RhinoMath.DefaultAngleTolerance, True)
                self.NCShiftX=self.SizeX*-1/2
                return [brep]

            elif self.NCType==NCTypes().Saw:
                brep=FeatureFactory().Saw(plane=self.Plane,size_x=self.SizeX,size_y=self.SizeY,size_z=self.NCCutSpace)
                #self.Brep.Faces.SplitKinkyFaces(Rhino.RhinoMath.DefaultAngleTolerance, True)
                return [brep]
                
        return None
            
    def __str__(self):
        
        #loggin.info("@Feature.__str__()")

        string="Feature-Instance:\n"
        string+="Name: ".ljust(20)+str(self.Name)+"\n"
        string+="Create: ".ljust(20)+str(self.Create)+"\n"
        string+="File: ".ljust(20)+str(self.File)+"\n"
        string+="ObjectID: ".ljust(20)+str(self.ObjectID)+"\n"
        string+="Text: ".ljust(20)+str(self.Text)+"\n"
        string+="Layer: ".ljust(20)+str(self.Layer)+"\n"
        string+="Axis: ".ljust(20)+str(self.Axis.ToString())+"\n"
        string+="Angle: ".ljust(20)+str(self.Angle)+"\n"
        string+="Spacing: ".ljust(20)+str(self.Spacing)+"\n"
        string+="Reverse: ".ljust(20)+str(self.Reverse)+"\n"
        string+="Shrink: ".ljust(20)+str(self.Shrink)+"\n"
        string+="Plane: ".ljust(20)+str(self.Plane)+"\n"
        string+="Ro: ".ljust(20)+str(self.Ro)+"\n"
        string+="Weight: ".ljust(20)+str(self.Weight)+"\n"
        string+="SizeX: ".ljust(20)+str(self.SizeX)+"\n"
        string+="SizeY: ".ljust(20)+str(self.SizeY)+"\n"
        string+="SizeZ: ".ljust(20)+str(self.SizeZ)+"\n"
        string+="UnrolX: ".ljust(20)+str(self.UnrolX)+"\n"
        string+="UnrolY: ".ljust(20)+str(self.UnrolY)+"\n"
        string+="UnrolZ: ".ljust(20)+str(self.UnrolZ)+"\n"
        string+="Radius: ".ljust(20)+str(self.Radius)+"\n"
        string+="NCCreate: ".ljust(20)+str(self.NCCreate)+"\n"
        string+="NCType: ".ljust(20)+str(self.NCType)+"\n"
        string+="NCNachlauf: ".ljust(20)+str(self.NCNachlauf)+"\n"
        string+="NCCutSpace: ".ljust(20)+str(self.NCCutSpace)+"\n"
        string+="NCDiameter: ".ljust(20)+str(self.NCDiameter)+"\n"
        string+="NCShiftX: ".ljust(20)+str(self.NCShiftX)+"\n"
        string+="NCShiftY: ".ljust(20)+str(self.NCShiftY)+"\n"
        string+="NCShiftZ: ".ljust(20)+str(self.NCShiftZ)+"\n"
        string+="NCXYCut: ".ljust(20)+str(self.NCXYCut)+"\n"
        string+="Notes: ".ljust(20)+str(self.Notes)+"\n"
        string+="LOD: ".ljust(20)+str(self.LOD)+"\n"
        string+="Color: ".ljust(20)+str(self.Color)+"\n"
        string+="RhinoMat: ".ljust(20)+str(self.RhinoMat)+"\n"
        
        return string
    
    def Copy(self,plane=None):
        
        #loggin.info("@Feature.Copy()")

        brep,objectid,axis=None,None,None
        if self.Brep!=None:
            if self.Brep.ObjectType==Rhino.DocObjects.ObjectType.Brep:
                brep=self.Brep.DuplicateBrep()
            elif self.Brep.ObjectType==Rhino.DocObjects.ObjectType.Curve:
                brep=self.Brep.Duplicate()
        
        curve=None
        if self.Curve!=None:
            curve=self.Curve.Duplicate()
        
        if self.ObjectID!=None:
            objectid=rs.CopyObject(self.ObjectID)
            
        if self.Axis!=None:
            if isinstance(self.Axis,Rhino.Geometry.Line):
                axis=Rhino.Geometry.Line(self.Axis.From,self.Axis.To)
            
        newfeat=Feature(
        name=self.Name,
        create=False,
        file=self.File,
        objectid=objectid,
        brep=brep,
        text=self.Text,
        layer=self.Layer,
        axis=axis,
        angle=self.Angle,
        spacing=self.Spacing,
        reverse=self.Reverse,
        shrink=self.Shrink,
        plane=Rhino.Geometry.Plane(self.Plane),
        ro=self.Ro,
        sizex=self.SizeX,
        sizey=self.SizeY,
        sizez=self.SizeZ,
        unrolx=self.UnrolX,
        unroly=self.UnrolY,
        unrolz=self.UnrolZ,
        radius=self.Radius,
        nccreate=self.NCCreate,
        nctype=self.NCType,
        ncnachlauf=self.NCNachlauf,
        nccutspace=self.NCCutSpace,
        ncdiameter=self.NCDiameter,
        ncshiftx=self.NCShiftX,
        ncshifty=self.NCShiftY,
        ncshiftz=self.NCShiftZ,
        ncxycut=self.NCXYCut,
        curve=curve,
        lod=self.LOD,
        color=self.Color,
        rhinomat=self.RhinoMat)
        
        newfeat.Create=True
            
        if plane!=None:
            newfeat.Orient(planeto=plane)
        
        return newfeat
    
    def Orient(self,planeto,planefrom=None):
        
        #loggin.info("@Feature.Orient()")

        targetplane=Rhino.Geometry.Plane(planeto)  
        if planefrom!=None:
            refplane=Rhino.Geometry.Plane(planefrom)  
        else:
            refplane=self.Plane 
            
        xform =Rhino.Geometry.Transform.PlaneToPlane(refplane,targetplane)
        
        if self.Brep!=None:
            self.Brep.Transform(xform)
        
        if self.Curve!=None:
            self.Curve.Transform(xform)
            
        if self.ObjectID!=None:
            rs.TransformObject(self.ObjectID,xform)
        
        if self.Axis!=None:
            self.Axis.Transform(xform)
        
        if planefrom!=None:
            self.Plane.Transform(xform)
        else:
            self.Plane=targetplane
        
        return None
    
    def Show(self,context):

        #loggin.info("@Feature.Show()")

        if self.ObjectID!=None and self.Brep==None:
            return True
        elif self.ObjectID!=None and self.Brep!=None:
            rs.DeleteObject(self.ObjectID)
        
        if isinstance(self.Brep,Rhino.Geometry.Brep):
            brep_=self.Brep.DuplicateBrep()
            brep_.Faces.SplitFacesAtTangents()
            objectid_=context.doc.Objects.AddBrep(brep_)
            if rs.IsObject(objectid_):
                self.ObjectID=objectid_
                self.Brep=brep_  
            else:
                self.ObjectID=context.doc.Objects.AddBrep(self.Brep)
                if not rs.IsObject(self.ObjectID):
                    self.ObjectID=None
                    return False
        else:
            brep=self.GenNCBreps()
            if brep!=None:
                la="!!!nc processing vis!!!"
                rs.AddLayer(la)
                [rs.ObjectLayer(context.doc.Objects.AddBrep(x),la) for x in brep]
            else:
                return False
        return True
    
    def Points(self):
        
        #loggin.info("@Feature.Points()")

        points=[]
        if self.Brep!=None:
            if self.Brep.ObjectType==Rhino.DocObjects.ObjectType.Curve:
                if isinstance(self.Brep,Rhino.Geometry.LineCurve):
                    points=[self.Brep.PointAtStart,self.Brep.PointAtEnd]
                elif isinstance(self.Brep,Rhino.Geometry.PolylineCurve):
                    points=[self.Brep.Point(i) for i in range(0,self.Brep.PointCount)]
                elif isinstance(self.Brep,Rhino.Geometry.NurbsCurve):
                    points=[item.Location for item in self.Brep.Points]
            
        return points
    
    def ToDic(self,savebreps=False,context=None):
        
        #loggin.info("@Feature.ToDic()")

        if savebreps and context !=None:
            if self.ObjectID==None and self.Brep!=None:
                self.ObjectID=sc.doc.Objects.AddBrep(self.Brep)
                rs.ObjectLayer(self.ObjectID,self.Layer)
                self.SaveBrep=True

        axis=None
        if isinstance(self.Axis,int):
            axis=self.Axis
        elif self.Axis.GetType()==Rhino.Geometry.LineCurve:
            axis=[[self.Axis.Line.From.X,self.Axis.Line.From.Y,self.Axis.Line.From.Z],[self.Axis.Line.To.X,self.Axis.Line.To.Y,self.Axis.Line.To.Z]]
        elif self.Axis.GetType()==Rhino.Geometry.Line:
            axis=[[self.Axis.From.X,self.Axis.From.Y,self.Axis.From.Z],[self.Axis.To.X,self.Axis.To.Y,self.Axis.To.Z]]
            
        dic= {"TYP":"Feature",
        "Name":self.Name,
        "Create":self.Create,
        "File":self.File,
        "ObjectID":str(self.ObjectID),
        "Text":self.Text,
        "Layer":self.Layer,
        "Axis":axis,
        "Angle":self.Angle,
        "Spacing":self.Spacing,
        "Reverse":self.Reverse,
        "Shrink":self.Shrink,
        "Plane":[[self.Plane.Origin.X,self.Plane.Origin.Y,self.Plane.Origin.Z],[self.Plane.XAxis.X,self.Plane.XAxis.Y,self.Plane.XAxis.Z],[self.Plane.YAxis.X,self.Plane.YAxis.Y,self.Plane.YAxis.Z]],
        "Ro":self.Ro,
        "Weight":self.Weight,
        "SizeX":self.SizeX,
        "SizeY":self.SizeY,
        "SizeZ":self.SizeZ,
        "UnrolX":self.UnrolX,
        "UnrolY":self.UnrolY,
        "UnrolZ":self.UnrolZ,
        "Radius":self.Radius,
        "NCCreate":self.NCCreate,
        "NCType":self.NCType,
        "NCNachlauf":self.NCNachlauf,
        "NCCutSpace":self.NCCutSpace,
        "NCDiameter":self.NCDiameter,
        "NCShiftX":self.NCShiftX,
        "NCShiftY":self.NCShiftY,
        "NCShiftZ":self.NCShiftZ,
        "NCXYCut":self.NCXYCut,
        "SaveBrep":self.SaveBrep,
        "LOD":self.LOD,
        "Color":self.Color,
        "RhinoMat":self.RhinoMat
        }
        return dic

    def ToDic2(self,path_key_map=""):

        #loggin.info("@Feature.ToDic()")

        dic={}

        if path_key_map=="":
            path_key_map=PATH_FEATURE_MAP
        
        mapkey=Archive().FromJSON(path_key_map)
        
        for key in self.__dict__: 
            val= self.__dict__[key]
            if key in mapkey:
                dic[mapkey[key]]=val
                
        return dic

    def ToSheetMarker(self):
        
        #loggin.info("@Feature.ToSheetMarker()")

        if self.NCType==NCTypes().Text:
            text=Rhino.Geometry.TextEntity()
            text.Plane=self.Plane
            text.Text=self.Text
            return SheetMarker(plane=self.Plane,text=self.Text,txtheight=self.SizeY,justification=self.Justification)
            
        elif self.NCType==NCTypes().Bolt:
            return SheetMarker(points=[self.Plane.Origin],diameter=self.SizeX)
        
        elif self.NCType==NCTypes().Silhouette:
            if self.Brep!=None:
                sil=Rhino.Geometry.Brep.CreateContourCurves(self.Brep,self.Plane)
                if len(sil)==1:
                    return SheetMarker(curve=sil[1],text=self.Text,plane=self.Plane)
        
        return None
        
    def FromDic(self,dic):
        
        #loggin.info("@Feature.FromDic()")

        for key in dic:
            if dic[key]=="None":
                dic[key]=None
        
        if dic["TYP"]=="Feature":
            self.Name=dic["Name"]
            self.Create=dic["Create"]
            self.File=dic["File"]
            self.ObjectID=dic["ObjectID"]
            self.Text=dic["Text"]
            self.Layer=dic["Layer"]
            self.Axis=Rhino.Geometry.Line(Rhino.Geometry.Point3d(dic["Axis"][0][0],dic["Axis"][0][1],dic["Axis"][0][2]),Rhino.Geometry.Point3d(dic["Axis"][1][0],dic["Axis"][1][1],dic["Axis"][1][2]))
            self.Angle=dic["Angle"]
            self.Spacing=dic["Spacing"]
            self.Reverse=dic["Reverse"]
            self.Shrink=dic["Shrink"]
            self.Plane=Rhino.Geometry.Plane(Rhino.Geometry.Point3d(dic["Plane"][0][0],dic["Plane"][0][1],dic["Plane"][0][2]),Rhino.Geometry.Vector3d(dic["Plane"][1][0],dic["Plane"][1][1],dic["Plane"][1][2]),Rhino.Geometry.Vector3d(dic["Plane"][2][0],dic["Plane"][2][1],dic["Plane"][2][2])) 
            self.Ro=dic["Ro"]
            self.Weight=dic["Weight"]
            self.SizeX=dic["SizeX"]
            self.SizeY=dic["SizeY"]
            self.SizeZ=dic["SizeZ"]
            self.UnrolX=dic["UnrolX"]
            self.UnrolY=dic["UnrolY"]
            self.UnrolZ=dic["UnrolZ"]
            self.Radius=dic["Radius"]
            self.NCCreate=dic["NCCreate"]
            self.NCType=dic["NCType"]
            self.NCNachlauf=dic["NCNachlauf"]
            self.NCCutSpace=dic["NCCutSpace"]
            self.NCDiameter=dic["NCDiameter"]
            self.NCShiftX=dic["NCShiftX"]
            self.NCShiftY=dic["NCShiftY"]
            self.NCShiftZ=dic["NCShiftZ"]
            self.NCXYCut=dic["NCXYCut"]
            self.LOD=dic["LOD"]
            self.Color=dic["Color"]
            self.RhinoMat=dic["RhinoMat"]
            
            self.__BrepFactory()
            
            if dic["SaveBrep"]==True:
                self.Brep=rs.coercebrep(self.ObjectID)
                if self.Brep==None:
                    print ("ObjectID not found: Feature-"+self.Name)
                else:
                    rs.DeleteObject(self.ObjectID)
                    self.ObjectID=None
        
        return self
            
    def CleanUp(self):
        
        #loggin.info("@Feature.CleanUp()")

        if self.ObjectID!=None:
            if rs.IsObject(self.ObjectID):
                rs.DeleteObject(self.ObjectID)
        
        return None        

    def UpdateDimension(self):
        
        if isinstance(self.SizeX,int):self.SizeX=float(self.SizeX)
        if isinstance(self.SizeY,int):self.SizeY=float(self.SizeY)
        if isinstance(self.SizeZ,int):self.SizeZ=float(self.SizeZ)

        self.Dimension="{0:.1f}x{1:.1f}x{2:.1f}".format(self.SizeX,self.SizeY,self.SizeZ)
        return True

    def UpdateArea(self,area=None):
        if area==None:
            self.Area=(self.UnrolX*self.UnrolY)/1000.**2
            if int(self.Area)==0:
                self.Area=(self.SizeX*self.SizeY)/1000.**2
        else:
            self.Area=area
        return True


class FeatureFactory:
    
    def __init__(self):

        #loggin.info("@FeatureFactory.__init__()")

        pass
    
    def Text(self,text="this is a text brep",size_y=10.,size_z=3.,plane=None,justification=None):
        
        #loggin.info("@FeatureFactory.Text()")

        if plane==None:
            plane=Rhino.Geometry.Plane.WorldXY
        else:
            plane=Rhino.Geometry.Plane(plane)
        shift_z=size_z/-2.
        return Text3D().GenBreps(text,plane,size_z,shift_z,size_y)
        
    def Hole(self,diameter=10,size_z=-10,plane=None):

        #loggin.info("@FeatureFactory.Hole()")

        if plane==None:
            plane=Rhino.Geometry.Plane.WorldXY
        else:
            plane=Rhino.Geometry.Plane(plane)
        if size_z<0:
            plane.Origin+=plane.ZAxis*size_z
            size_z*=-1
        
        return Rhino.Geometry.Cylinder(Rhino.Geometry.Circle(plane,diameter/2),size_z).ToBrep(True,True)
    
    def EHole(self,size_x=50,diameter=20,size_z=-20,plane=None):

        #loggin.info("@FeatureFactory.EHole()")

        if plane==None:
            plane=Rhino.Geometry.Plane.WorldXY
        else:
            plane=Rhino.Geometry.Plane(plane)
        if size_z<0:
            plane.Origin+=plane.ZAxis*size_z
            size_z*=-1
        
        radius=diameter/2
        vx=plane.XAxis
        vy=plane.YAxis
        vz=plane.ZAxis
        
        vx.Unitize()
        vy.Unitize()
        vz.Unitize()

        cps=plane.Origin-vx*(size_x/2)
        cpe=plane.Origin+vx*(size_x/2)
            
        pcurve=Rhino.Geometry.PolyCurve()
        pcurve.Append(Rhino.Geometry.Arc(cps-vy*radius,cps-vx*radius,cps+vy*radius))
        pcurve.Append(Rhino.Geometry.Line(cps+vy*radius,cpe+vy*radius))
        pcurve.Append(Rhino.Geometry.Arc(cpe+vy*radius,cpe+vx*radius,cpe-vy*radius))
        pcurve.Append(Rhino.Geometry.Line(cpe-vy*radius,cps-vy*radius))
        pcurve.Reverse()
        
        return Rhino.Geometry.Extrusion().Create(pcurve,size_z,True).ToBrep()
    
    def RHole(self,size_x=50,size_y=25,size_z=-50,cornerradius=5,plane=None):

        #loggin.info("@FeatureFactory.RHole()")

        if plane==None:
            plane=Rhino.Geometry.Plane.WorldXY
        else:
            plane=Rhino.Geometry.Plane(plane)
        if size_z<0:
            plane.Origin+=plane.ZAxis*size_z
            size_z*=-1
        

        r=cornerradius
        if r >0:
            vx=plane.XAxis
            vy=plane.YAxis
            vz=plane.ZAxis
            
            vx.Unitize()
            vy.Unitize()
            vz.Unitize()
            
            dia1=-vx+vy
            dia2=vx+vy
            dia3=vx-vy
            dia4=-vx-vy
            
            dia1.Unitize()
            dia2.Unitize()
            dia3.Unitize()
            dia4.Unitize()
            
            cp1=plane.Origin-vx*((size_x/2)-r)+vy*((size_y/2)-r)
            cp2=plane.Origin+vx*((size_x/2)-r)+vy*((size_y/2)-r)
            cp3=plane.Origin+vx*((size_x/2)-r)-vy*((size_y/2)-r)
            cp4=plane.Origin-vx*((size_x/2)-r)-vy*((size_y/2)-r)
            
            pcurve=Rhino.Geometry.PolyCurve()
            pcurve.Append(Rhino.Geometry.Arc(cp1-vx*r,cp1+dia1*r,cp1+vy*r))
            pcurve.Append(Rhino.Geometry.Line(cp1+vy*r,cp2+vy*r))
            pcurve.Append(Rhino.Geometry.Arc(cp2+vy*r,cp2+dia2*r,cp2+vx*r))
            pcurve.Append(Rhino.Geometry.Line(cp2+vx*r,cp3+vx*r))
            pcurve.Append(Rhino.Geometry.Arc(cp3+vx*r,cp3+dia3*r,cp3-vy*r))
            pcurve.Append(Rhino.Geometry.Line(cp3-vy*r,cp4-vy*r))
            pcurve.Append(Rhino.Geometry.Arc(cp4-vy*r,cp4+dia4*r,cp4-vx*r))
            pcurve.Append(Rhino.Geometry.Line(cp4-vx*r,cp1-vx*r))
            pcurve.Reverse()
        else:
            vx=plane.XAxis
            vy=plane.YAxis
            vz=plane.ZAxis
            
            vx.Unitize()
            vy.Unitize()
            vz.Unitize()
            
            cp1=plane.Origin-vx*((size_x/2))+vy*((size_y/2))
            cp2=plane.Origin+vx*((size_x/2))+vy*((size_y/2))
            cp3=plane.Origin+vx*((size_x/2))-vy*((size_y/2))
            cp4=plane.Origin-vx*((size_x/2))-vy*((size_y/2))
            
            pcurve=Rhino.Geometry.PolyCurve()
            pcurve.Append(Rhino.Geometry.Line(cp1,cp2))
            pcurve.Append(Rhino.Geometry.Line(cp2,cp3))
            pcurve.Append(Rhino.Geometry.Line(cp3,cp4))
            pcurve.Append(Rhino.Geometry.Line(cp4,cp1))
            pcurve.Reverse()
        
        return Rhino.Geometry.Extrusion().Create(pcurve,size_z,True).ToBrep()
        
    def Saw(self,plane,size_x=0,size_y=0,size_z=0):

        #loggin.info("@FeatureFactory.Saw()")

        plane=Rhino.Geometry.Plane(plane)
        if size_x==0:
            size_x=1000
        if size_y==0:
            size_y=1000
        if size_z!=0:
            plane.Origin+=plane.ZAxis*-size_z
            
        plane=Rhino.Geometry.PlaneSurface(plane,Rhino.Geometry.Interval(-size_x,size_x),Rhino.Geometry.Interval(-size_y,size_y))
        #box=Rhino.Geometry.Box(plane,Rhino.Geometry.Interval(-size_x,size_x),Rhino.Geometry.Interval(-size_y,size_y),Rhino.Geometry.Interval(0,size_z))
        return plane.ToBrep()
    

class FeaturePositioner:
    
    def __init__(self,axis,feature,spacing=[50,200,50],count=None,plane=None):

        #loggin.info("@FeaturePositioner.__init__()")
        
        self.Error=""
        self.Axis=axis
        self.Feature=feature
        self.Spacing=spacing
        self.Count=count
        self.Plane=Rhino.Geometry.Plane.WorldXY
        if plane!=None:
            self.Plane=plane
        
        self.__Planes=self.__GetPlanes()
        self.Features=self.__Position()
        
    def __Position(self):

        #loggin.info("@FeaturePositioner.__Position()")

        feats=[]
        for plane in self.__Planes:
            feat=self.Feature.Copy()
            feat.Orient(plane)
            feats.append(feat)
        return feats
        
    def __GetPlanes(self):
        
        #loggin.info("@FeaturePositioner.__GetPlanes()")

        planes=[]
        vx=self.Axis.Direction
        vx.Unitize()
        l=self.Axis.From.DistanceTo(self.Axis.To)
        lred=l-(self.Spacing[0]+self.Spacing[2])
        if self.Count==None:
            self.Count=int(lred/self.Spacing)
            
        if self.Count==0:
            return planes
        if self.Count==1:
            plc=Rhino.Geometry.Plane(self.Plane)
            plc.Origin=(self.Axis.From+self.Axis.To)/2
            planes.append(plc)
        else:
            step=lred/(self.Count-1)
            
            for i in range(0,self.Count):
                plc=Rhino.Geometry.Plane(self.Plane)
                plc.Origin=self.Axis.From+vx*self.Spacing[0]+vx*(step*i)
                planes.append(plc)
        
        return planes
       

class Part(Archive):
    
    def __init__(self,attrib=None,feature=None,context=None,dic=None):
        
        #loggin.info("@Part.__init__()")

        self.Context=context
        self.Error=""
        if attrib==None:
            attrib=Attrib()
        self.Attrib=attrib  
        if feature==None:
            self.Features=[Feature()] #KEF auf 0
        else:
            self.Features=[feature]
        if dic==None:
            dic={}
        self.Dictionary=dic

    def __str__(self):
        
        #loggin.info("@Part.__str__()")

        string="Part+Inheritance-Instance:\n"
        string+=str(self.Attrib)+"\n"
        for feat in self.Features:
            string+=str(feat)
        
        return string
    
    def __ApplyFeatures(self,features,tolerance,append=False):
        
        #loggin.info("@Part.__ApplyFeatures()")

        #for feat in features:
        #    if feat.ObjectID!=None and feat.Brep==None: 
        #        feat.Brep=rs.coercebrep(feat.ObjectID)
        if self.Features[0].Brep.SolidOrientation==Rhino.Geometry.BrepSolidOrientation.Inward:
            self.Features[0].Brep.Flip()

        for feat in features:
            res=[]
            featbreps=[]
            #ist ein brep im feature hinterlegt
            if feat.Brep!=None:
                featbreps.append(feat.Brep)
            #falls es ein gueltiges nc feature ist werden hier die nc breps angefuegt
            featbreps+=feat.GenNCBreps()
            #processing
            for featbrep in featbreps:
                if isinstance(featbrep,Rhino.Geometry.Brep):
                    if featbrep.IsSolid:
                        featbrep.Faces.SplitKinkyFaces(Rhino.RhinoMath.DefaultAngleTolerance, True)
                        if featbrep.SolidOrientation==Rhino.Geometry.BrepSolidOrientation.Inward:
                            featbrep.Flip()
                        res=Rhino.Geometry.Brep.CreateBooleanDifference(self.Features[0].Brep,featbrep,tolerance)
                    else:
                        res=self.Features[0].Brep.Split(featbrep,tolerance)

                #ergebnis behandeln
                if len(res)==1:
                    res=res[0]
                elif len(res)>1:
                    #option 1 via cut direction
                    if feat.NCType==NCTypes().Saw  and len(res)==2:
                        amp=Rhino.Geometry.AreaMassProperties.Compute(res[0])
                        if rs.XformWorldToCPlane(amp.Centroid,feat.Plane).Z>0:
                            res=res[1]
                        else:
                            res=res[0]
                    else:
                        maxvol=0
                        maxid=-1
                        for zahl,so in enumerate(res,0):
                            vol=so.GetBoundingBox(True).Volume
                            if vol>maxvol:
                                maxvol=vol
                                maxid=zahl
                        res=res[maxid]
                    #anpassung der achse bei ebenen beschnitt
                    if feat.NCType==NCTypes().Saw and feat.Brep==None:
                        self.Features[0].Axis.ExtendThroughBox(self.BoundingBox(getbox=True))
                else:
                    continue

                if isinstance(res,Rhino.Geometry.Brep):
                    if res.IsValid:
                        if not res.IsSolid:
                            res=res.CapPlanarHoles(tolerance)#
                        if isinstance(res,Rhino.Geometry.Brep):
                            if res.IsValid:
                                self.Features[0].Brep=res
                        else:
                            print "brep is not valid after capping"    
                    else:
                        print "brep is not valid after cutting"                
        if append:
            self.Features+=features
        
        if self.Features[0].ObjectID!=None and self.Context!=None:
            rs.EnableRedraw(False)
            rs.DeleteObject(self.Features[0].ObjectID)
            self.Features[0].ObjectID=self.Context.doc.Objects.AddBrep(self.Features[0].Brep)
            self.UpdateObjectProperties()
            rs.EnableRedraw(False)


        return True
                
    def Brep(self,brep=None):

        #loggin.info("@Part.Brep()")

        if brep==None:
            if self.Features[0].Brep==None and self.Features[0].ObjectID!=None: 
                return rs.coercebrep( self.Features[0].ObjectID)
            else:
                if isinstance(self.Features[0].Brep,Rhino.Geometry.Brep):
                    return self.Features[0].Brep
                else:
                    return None
        else:
            if isinstance(brep,System.Guid):
                brepgeo=rs.coercebrep(brep)
                if brepgeo!=None:
                    self.Features[0].Brep=brepgeo
                    self.Features[0].ObjectID=brep
                    return self.Features[0].Brep
            elif isinstance(brep,Rhino.Geometry.Brep):
                self.Features[0].Brep=brepgeo
                return self.Features[0].Brep

        return None
                
    def Weight(self):
        
        #loggin.info("@Part.Weight()")

        weight=0
        brep=self.Brep()
        if brep!=None:
            if brep.IsSolid:
                #print "---brep ok!"
                weight= (abs(brep.GetVolume())*UnitFactor().Factor**3)*self.Features[0].Ro
            else:
                weight= ((brep.GetArea()*self.Features[0].UnrolZ)*UnitFactor().Factor**3)*self.Features[0].Ro
           
        if weight<=0:
            return self.Features[0].Weight
            
        return weight
        
    def BoundingBox(self,plane=None,getbox=False):
        
        #loggin.info("@Part.BoundingBox()")

        brep=self.Brep()
        if brep!=None:
            if plane==None:
                xform = Rhino.Geometry.Transform.ChangeBasis(Rhino.Geometry.Plane.WorldXY, self.Features[0].Plane)
                bbx=brep.GetBoundingBox(xform)
            else:
                xform = Rhino.Geometry.Transform.ChangeBasis(Rhino.Geometry.Plane.WorldXY, plane)
                bbx=brep.GetBoundingBox(xform)
            if not getbox:
                return bbx.Diagonal.X,bbx.Diagonal.Y,bbx.Diagonal.Z
            else:
                if plane!=None:
                    xform2=Rhino.Geometry.Transform.ChangeBasis(plane,Rhino.Geometry.Plane.WorldXY)
                    return Rhino.Geometry.Box(plane,bbx)
                else:
                    xform2=Rhino.Geometry.Transform.ChangeBasis(self.Features[0].Plane,Rhino.Geometry.Plane.WorldXY)
                    return Rhino.Geometry.Box(self.Features[0].Plane,bbx)
                
        return self.Features[0].SizeX,self.Features[0].SizeY,self.Features[0].SizeZ
    
    def UpdateObjectProperties(self):
        
        #loggin.info("@Part.UpdateObjectProperties()")

        if self.Features[0].ObjectID!=None:
            #if not rs.IsObject(self.Features[0].ObjectID):
            #    rs.AddTextDot("",self.Features[0].Axis.From)
            #    self.Error+="objectid not found @Part.UpdateObjectProperties()"
            #    return False
            if self.Features[0].Layer!="" and rs.IsObject(self.Features[0].ObjectID):
                if not rs.IsLayer(self.Features[0].Layer):
                    rs.AddLayer(self.Features[0].Layer)
                rs.ObjectLayer(self.Features[0].ObjectID,self.Features[0].Layer)
                rs.ObjectName(self.Features[0].ObjectID,self.Attrib.PosNo())
                if self.Features[0].Color!=None:
                    rs.ObjectColor(self.Features[0].ObjectID,self.Features[0].Color)
                if self.Features[0].RhinoMat!=None:
                    obj=sc.doc.Objects.Find(self.Features[0].ObjectID)
                    attr=obj.Attributes
                    #print self.Features[0].RhinoMat
                    attr.MaterialIndex = self.Features[0].RhinoMat
                    attr.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromObject;
                    obj.CommitChanges()
                    
        self.Features[0].Weight=self.Weight()
        self.Features[0].SizeX,self.Features[0].SizeY,self.Features[0].SizeZ=self.BoundingBox()
        self.Features[0].UpdateDimension()
        self.Features[0].UpdateArea()

        return True
        
    def Copy(self,plane=None):
        
        #loggin.info("@Part.Copy()")

        newpart=Part(attrib=self.Attrib.Copy(),feature=self.Features[0].Copy(),dic=copy.deepcopy(self.Dictionary))
        for i in range(1,len(self.Features)):
            newpart.Features.append(self.Features[i].Copy())
        
        if plane!=None:
            newpart.Orient(plane)
        
        return newpart 
        
    def Orient(self,planeto,planefrom=None):
        
        #loggin.info("@Part.Orient()")

        if planefrom==None:
            planefrom=Rhino.Geometry.Plane(self.Features[0].Plane)
        for i in range(0,len(self.Features)):
            self.Features[i].Orient(planeto=planeto,planefrom=planefrom)
            
        return None
    
    def ApplyFeatures(self,tolerance,features=None,lod=500):
        
        #loggin.info("@Part.ApplyFeatures()")

        if self.Features[0].ObjectID==None and self.Features[0].Brep==None:
            self.Error+="no object and no brep associated @ Part.ApplyFeatures()\n"
            return False
        elif self.Features[0].ObjectID!=None and self.Features[0].Brep==None:
            res=rs.coercebrep(self.Features[0].ObjectID)
            self.Features[0].Brep=res
            if res==None:
                self.Error+="no brep konvert possible @ Part.ApplyFeatures()\n"
                return False
            elif not res.IsSolid:
                self.Error+="no brep konvert possible @ Part.ApplyFeatures()\n"
                return False
        
        append=True
        if features==None:
            features=self.Features[1:]
            append=False
        else:
            if not isinstance(features,list):
                features=[features]
        features=[feat for feat in features if feat.LOD<=lod]
        if len(features)==0:
            return False
        
        return self.__ApplyFeatures(features,tolerance,append)
    
    def Show(self,context,group=None,block=False,writeattribtoobject=False,path_attrib_key_map="",path_feat_key_map="",path_attrib_fin_map=""):
        
        #loggin.info("@Part.Show()")

        userdic=None 
        
        res=self.Features[0].Show(context)
        if res:

            if block:
                if self.Attrib.Block==True:
                    dot=True
                    if self.Attrib.ID=="":
                        dot=False
                        self.Attrib.ID="1"
                    bln=self.Attrib.PosNo()
                    if bln in rs.BlockNames():
                        cn=1
                        if dot:
                            while bln+"."+str(cn) in rs.BlockNames():
                                cn+=1
                            bln+="."+str(cn)
                        else:
                            while bln in rs.BlockNames():
                                cn+=1
                                self.Attrib.ID=str(cn)
                                bln=self.Attrib.PosNo()
            
            self.UpdateObjectProperties()

            if writeattribtoobject:
                dicx=self.Attrib.ToDic2(path_key_map=path_attrib_key_map,path_fin_map=path_attrib_fin_map)
                dicx.update(self.Features[0].ToDic2(path_key_map=path_feat_key_map))
                self.WriteObjAttrib(self.Features[0].ObjectID,dicx)
            
            if group!=None:
                rs.AddObjectsToGroup([self.Features[0].ObjectID],group)
            
            if block:
                if self.Attrib.Block==True:
                    bl=rs.AddBlock([self.Features[0].ObjectID],[0,0,0],bln,True)
                    if bl!=None:
                        bli= rs.InsertBlock(bl,[0,0,0])
                        rs.AddLayer(self.Features[0].Layer)
                        rs.ObjectLayer(bli,self.Features[0].Layer)
                        rs.DeleteObject(self.Features[0].ObjectID)
                        self.Features[0].ObjectID=None
                        return bli
                else:
                    return self.Features[0].ObjectID                
            else:
                return self.Features[0].ObjectID
        else:
            return None
        
        return None
        
    def ShowFeatures(self,context):
        
        #loggin.info("@Part.ShowFeatures()")

        for i,feat in enumerate(self.Features,0):
            if i>0:
                feat.Show(context)
        
        return True
        
    def ToAPArtikel(self,struktur=0,menge=None):
        
        #loggin.info("@Part.ToAPArtikel()")

        if "create" in self.Dictionary.Keys:
            if self.Dictionary["create"]==0:
                return None
        
        self.UpdateObjectProperties()  
        
        apa=APArtikel()
        apa.VBME=self.Attrib.VBME
        apa.Struktur=struktur
        apa.Artikel=self.Attrib.APVorlage
        apa.Name2=self.Attrib.ZusatzText 
        #x=self.Attrib.Menge
        if menge==None:
            apa.Menge=self.Attrib.Menge
        else:
            if menge<self.Attrib.Menge:
                apa.Menge=self.Attrib.Menge
            else:
                apa.Menge=menge
        apa.ME="Stück"
        apa.Laenge=self.Features[0].SizeX
        apa.Breite=self.Features[0].SizeY
        apa.Hoehe=self.Features[0].SizeZ
        #apa.Staerke=staerke
        apa.Gewicht=self.Features[0].Weight
        #apa.Material=material
        #apa.Zeichnung=zeichnung
        apa.ZeichnungPos=self.Attrib.PosNo()
        apa.ZText=self.Attrib.TextPos
        #apa.HerstStueli=herststueli
        apa.Einkauf=self.Attrib.Einkauf
        apa.Fertigung=self.Attrib.Fertigung
        apa.Auftrag=self.Attrib.Auftrag
        apa.Lager=self.Attrib.Lager
        #apa.Beistellung=beistellung
        #apa.Fremdmontage=fremdmontage
        apa.FinishCode=self.Attrib.FinishCode
        apa.MatCode=self.Attrib.MatCode
        apa.RawMat=self.Attrib.RawMat
        apa.UnrolX=self.Features[0].UnrolX
        apa.UnrolY=self.Features[0].UnrolY
        apa.UnrolZ=self.Features[0].UnrolZ
        
        if self.Attrib.SubASM!="":
            below=apa.Copy(strukturplus=1)
            apa.RawMat=""
            apa.ZeichnungPos+=self.Attrib.SubASM
            apa.Children=[below]
        return apa
       
    def ToDic(self,savebreps=False,context=None):

        #loggin.info("@Part.ToDic()")

        self.UpdateObjectProperties()
        return {"TYP":"Part","Features":[x.ToDic(savebreps,context) for x in self.Features],"Attrib":self.Attrib.ToDic(),"Dic":self.Dictionary}
    
    def FromDic(self,dic):
        
        #loggin.info("@Part.FromDic()")

        for key in dic:
            if dic[key]=="None":
                dic[key]=None
        
        self.Features=[]
        if dic["TYP"]=="Part":
            for i,item in enumerate(dic["Features"]):
                self.Features.append(Feature().FromDic(item))
            self.Attrib=Attrib().FromDic(dic["Attrib"])
            self.Dictionary=dic["Dic"]
            
        return self
        
    def LoadFromFile(self,path,id=0):
        
        #loggin.info("@Part.LoadFromFile()")

        rs.Command("-_import " + path + " _enter")
        lco=rs.LastCreatedObjects()
        if len(lco)>id:
            self.Features[0].ObjectID=lco
            
        return None
        
    def CleanUp(self):
        
        #loggin.info("@Part.CleanUp()")

        for f in self.Features:
            f.CleanUp()
            
        return None
        
        
class Profile(Part):
    
    def __init__(self,attrib=None,feature=None,context=None,dic=None):
        #print "note: profile direction == plane.XAxis"
        
        #loggin.info("@Profile.__init__()")

        self.NCPlane=None
        self.Context=context
        self.Error=""
        if attrib==None:
            attrib=Attrib()
        self.Attrib=attrib  
        if feature==None:
            self.Features=[Feature()] #KEF auf 0
        else:
            self.Features=[feature]
        if dic==None:
            dic={}
        self.Dictionary=dic   
        if len(self.Features)>0:
            if self.Features[0].Brep==None:
                self.__CreateFromFile()
    
    def __LoadFile(self):
        
        #loggin.info("@Profile.__LoadFile()")

        rcmd="_-Import %s _Enter" %(self.Features[0].File)
        rs.Command(rcmd)

        return rs.LastCreatedObjects()
                
    def __CreateFromFile(self):

        #loggin.info("@Profile.__CreateFromFile()")

        if self.Features[0].File!=None:
            qs=self.__LoadFile()
            if qs== None:
                print "failed to load profile -> canceled extrusion\nfilename: " +self.Features[0].File
                return False
        else:
            return False
            
        plane=Rhino.Geometry.Plane(Rhino.Geometry.Plane(Rhino.Geometry.Plane.WorldXY.Origin,Rhino.Geometry.Plane.WorldXY.YAxis*-1,Rhino.Geometry.Plane.WorldXY.ZAxis))
        xform1=Rhino.Geometry.Transform.ChangeBasis(plane,Rhino.Geometry.Plane.WorldXY)
        xform2=Rhino.Geometry.Transform.ChangeBasis(self.Features[0].Plane,Rhino.Geometry.Plane.WorldXY)
        xform=xform2*xform1
                
        created=False
        brep=None
        
        for obj in qs:
            con=rs.coercegeometry(obj)
            if isinstance(con,Rhino.Geometry.Brep) and not created:
                con.Transform(xform)
                brep=con.Faces[0].CreateExtrusion(Rhino.Geometry.LineCurve(self.Features[0].Axis), True)
                brep.Faces.SplitKinkyFaces(Rhino.RhinoMath.DefaultAngleTolerance, True)
                if brep==None:
                    return False
                else:
                    created=True
            elif con.ObjectType==Rhino.DocObjects.ObjectType.Curve:
                con.Transform(xform)
                self.Features.append(Feature(brep=con,nctype=NCTypes().Help))
                
        rs.DeleteObjects(qs)
        self.Features[0].Brep=brep
        
        return True
        
    def __NCPlane(self,plane=None):
        
        #loggin.info("@Profile.__NCPlane()")

        brep=self.Brep()
        if brep!=None:
            if plane==None:
                plane=Rhino.Geometry.Plane(self.Features[0].Plane)
            if plane==None:
                return None
            bbx=rs.BoundingBox(brep,plane)
            plane.Origin=bbx[4]
            #plane.Origin=bbx[rs.PointArrayClosestPoint(bbx,plane.Origin)]
            return plane
        
        return None
        
    def Copy(self,plane=None):
        
        #loggin.info("@Profile.Copy()")

        newprofile=Profile(attrib=self.Attrib.Copy(),feature=self.Features[0].Copy(),dic=copy.deepcopy(self.Dictionary))
        for i in range(1,len(self.Features)):
            newprofile.Features.append(self.Features[i].Copy())
        
        if plane!=None:
            newprofile.Orient(plane)
        
        return newprofile        
        
    def ToNCItem(self,vis=True,ncplane=None,parentlayer=""):
        #wenn ncplane nicht übergeben wird wird der profil.Features[0].Plane.Origin auf bbx[4] gesetzt 
        
        #loggin.info("@Profile.ToNCItem()")

        if self.Features[0].NCCreate==False:
            return None
        
        if ncplane==None:
            if self.NCPlane!=None:
               ncplane=self.NCPlane
        ncplane=self.__NCPlane(plane=ncplane)
        bbx=self.BoundingBox(plane=ncplane)
        #textbox=Rhino.Geometry.Brep.CreateFromBox(self.BoundingBox(plane=ncplane,getbox=True))
        #print self.Attrib.Menge
        nci=NCItem(ncplane,self.Attrib.PosNo(),self.Attrib.RawMat,bbx,vis=vis,visparentlayer=parentlayer,count=self.Attrib.Menge)
        
        for i in range(1,len(self.Features)):
            
            if self.Features[i].NCCreate==True:
                
                fplane=self.Features[i].Plane
                po=fplane.Origin+fplane.XAxis*self.Features[i].NCShiftX + fplane.YAxis*self.Features[i].NCShiftY + fplane.ZAxis*self.Features[i].NCShiftZ
                px=po+fplane.XAxis*self.Features[i].SizeX
                py=po+fplane.YAxis*self.Features[i].SizeY
                pz=po+fplane.ZAxis*self.Features[i].SizeZ
                
                if self.Features[i].Name=="":
                    self.Features[i].Name="not-defined"
                
                if self.Features[i].NCType==NCTypes().Text:
                    #umrechnung noetig da komische puma umrechnung stattfindet
                    #ppo=Rhino.Geometry.Intersect.Intersection.ProjectPointsToBreps([textbox],[po],fplane.ZAxis,0.01)
                    #ppx=Rhino.Geometry.Intersect.Intersection.ProjectPointsToBreps([textbox],[px],fplane.ZAxis,0.01)
                    #if len(ppo)!=2 or len(ppx)!=2 :
                    #    continue
                    #if rs.XformWorldToCPlane(ppo[0],fplane).Z>0:
                    #    po=ppo[0]
                    #else:
                    #    po=ppo[1]
                    #if rs.XformWorldToCPlane(ppx[0],fplane).Z>0:
                    #    px=ppx[0]
                    #else:
                    #    px=ppx[1]
                    nci.AddText(po,px,po+fplane.ZAxis,name=self.Features[i].Name,text=self.Features[i].Text,vis=True,visparentlayer=parentlayer)
                        
                elif self.Features[i].NCType==NCTypes().Hole:
                    nci.AddHole(po,pz,self.Features[i].Name,vis=True,visparentlayer=parentlayer)
                    
                elif self.Features[i].NCType==NCTypes().Thread:
                    nci.AddHole(po,pz,self.Features[i].Name,vis=True,visparentlayer=parentlayer)
                
                elif self.Features[i].NCType==NCTypes().EHole:
                    nci.AddEHole(po,pz,px,self.Features[i].Name,vis=True,visparentlayer=parentlayer)
                        
                elif self.Features[i].NCType==NCTypes().RHole:
                    nci.AddRHole(po,pz,px,self.Features[i].Name,vis=True,visparentlayer=parentlayer)
                    
                elif self.Features[i].NCType==NCTypes().Freemill:
                    nci.AddFreemill(po,pz,px,self.Features[i].Name,vis=True,visparentlayer=parentlayer)                    
                    
                elif self.Features[i].NCType==NCTypes().Saw:
                    if self.Features[i].SizeX!=0 and self.Features[i].SizeY!=0:     
                        axx=[po,px]
                        axy=[po,py]
                        #plane, name = "",cutspace=0,yzCut=0,vis=False,axisx=None,axisy=None,reverse=False,shrink=0,nachlauf=0,visparentlayer=""
                        nci.AddSaw(plane=self.Features[i].Plane,name= self.Features[i].Name,cutspace=self.Features[i].NCCutSpace,vis=True,axisx=axx,axisy=axy,nachlauf=self.Features[i].NCNachlauf,visparentlayer=parentlayer)
                    else:
                        nci.AddSaw(plane=self.Features[i].Plane, name= self.Features[i].Name, cutspace=self.Features[i].NCCutSpace, yzCut=self.Features[i].NCXYCut,vis=True,reverse=self.Features[i].Reverse,shrink=self.Features[i].Shrink,nachlauf=self.Features[i].NCNachlauf,visparentlayer=parentlayer)                
                            
        return nci
    
    def ToDic(self,savebreps=False,context=None):

        #loggin.info("@Profile.ToDic()")

        self.UpdateObjectProperties()
        return {"TYP":"Profile","Features":[x.ToDic(savebreps,context) for x in self.Features],"Attrib":self.Attrib.ToDic(),"Dic":self.Dictionary}
        
    def ToSheet(self):

        #loggin.info("@Profile.ToSheet()")

        pass
        
    def FromDic(self,dic,loadfile=False):
        
        #loggin.info("@Profile.FromDic()")

        for key in dic:
            if dic[key]=="None":
                dic[key]=None
        
        self.Features=[]
        if dic["TYP"]=="Profile":
            for i,item in enumerate(dic["Features"]):
                self.Features.append(Feature().FromDic(item))
            if loadfile==False:
                self.Features[0].File=None
            self.Attrib=Attrib().FromDic(dic["Attrib"])
            self.Dictionary=dic["Dic"]
            if len(self.Features)>0:
                if self.Features[0].Brep==None:
                    self.__CreateFromFile()
            
        return self
    
    
class Sheet(Part):
    
    def __init__(self,attrib=None,feature=None,context=None,dic=None):
        
        #loggin.info("@Sheet.__init__()")

        self.Context=context
        self.Error=""
        if attrib==None:
            attrib=Attrib()
        self.Attrib=attrib  
        if feature==None:
            self.Features=[Feature()] #KEF auf 0
        else:
            self.Features=[feature]
        if dic==None:
            dic={}
        self.Dictionary=dic
        self.Unroller=None
        
    def __Unroll(self,brep=None,text=None):
        
        #loggin.info("@Sheet.__Unroll()")

        if brep==None:
            brep=self.Brep()
        else:
            brep=self.Brep(brep=brep)
        if brep==None:
            print "no valid brep geo given and found"
            return False
        
        mat=0
        if self.Attrib.APVorlage!="":
            if "AL" in self.Attrib.APVorlage:
                mat=0
            if "VA" in self.Attrib.APVorlage:
                mat=1
            if "ST" in self.Attrib.APVorlage:
                mat=2
        else:
            print "no self.Attrib.APVorlage"
        
        if text!=None:
            if not isinstance(text,Rhino.Geometry.TextEntity):
                text=None
                
        if text==None:
            text=Rhino.Geometry.TextEntity()
            text.Plane=self.Features[0].Plane
            text.Text=self.Attrib.PosNo()
            
        sheetmarker=[SheetMarker(plane=text.Plane,text=text.Text,txtheight=10)]
        for i in range(1,len(self.Features)):
            temp=self.Features[i].ToSheetMarker()
            if temp!=None:
                sheetmarker.append(temp)
        
        #an den kastest sheetmarker shit anpassen
        self.Unroller=SheetUnroller(brep=brep,sheetmarker=sheetmarker,mat=mat)
        if self.Unroller.Error!="":
            self.Error+= self.Unroller.Error+"\n"
            self.Unroller=None
            return False
            
        return True
    
    def Copy(self,plane=None):
        
        #loggin.info("@Sheet.Copy()")

        newsheet=Sheet(attrib=self.Attrib.Copy(),feature=self.Features[0].Copy(),dic=copy.deepcopy(self.Dictionary))
        for i in range(1,len(self.Features)):
            newsheet.Features.append(self.Features[i].Copy())
        
        if plane!=None:
            newsheet.Orient(plane)
        
        return newsheet 
    
    def ToDrawing(self,brep=None,text=None):
        
        #loggin.info("@Sheet.ToDrawing()")

        if self.__Unroll(brep=brep,text=text):
            return self.Unroller.GenDrawing()
        return None
        
    def ToAPArtikel(self,struktur=0,menge=None):
        
        #loggin.info("@Sheet.ToAPArtikel()")

        if self.Unroller==None:
            self.__Unroll()
        if self.Unroller!=None:
            if isinstance(self.Unroller,SheetUnroller):    
                dim=self.Unroller.Dimensions()
                self.Features[0].UnrolX=dim.X
                self.Features[0].UnrolY=dim.Y
                self.Features[0].UnrolZ=dim.Z
                
        self.UpdateObjectProperties()  
        
        apa=APArtikel()
        #self.LFDNR=lfdnr
        apa.VBME="m2"
        apa.Struktur=struktur
        apa.Artikel=self.Attrib.APVorlage
        apa.Name2=self.Attrib.ZusatzText 
        
        if menge==None:
            apa.Menge=self.Attrib.Menge
        else:
            if menge<self.Attrib.Menge:
                apa.Menge=self.Attrib.Menge
            else:
                apa.Menge=menge
        
        #apa.Menge=self.Attrib.Menge
        apa.ME="Stück"
        apa.Laenge=self.Features[0].SizeX
        apa.Breite=self.Features[0].SizeY
        apa.Hoehe=self.Features[0].SizeZ
        #apa.Staerke=staerke
        apa.Gewicht=self.Features[0].Weight
        #apa.Material=material
        #apa.Zeichnung=zeichnung
        apa.ZeichnungPos=self.Attrib.PosNo()
        apa.ZText=self.Attrib.TextPos
        #apa.HerstStueli=herststueli
        apa.Einkauf=self.Attrib.Einkauf
        apa.Fertigung=self.Attrib.Fertigung
        apa.Auftrag=self.Attrib.Auftrag
        apa.Lager=self.Attrib.Lager
        #apa.Beistellung=beistellung
        #apa.Fremdmontage=fremdmontage
        apa.FinishCode=self.Attrib.FinishCode
        apa.MatCode=self.Attrib.MatCode
        apa.RawMat=self.Attrib.RawMat
        apa.UnrolX=self.Features[0].UnrolX
        apa.UnrolY=self.Features[0].UnrolY
        apa.UnrolZ=self.Features[0].UnrolZ
        
        return apa
    
    def ToDic(self,savebreps=False,context=None):

        #loggin.info("@Sheet.ToDic()")

        self.UpdateObjectProperties()
        return {"TYP":"Sheet","Features":[x.ToDic(savebreps,context) for x in self.Features],"Attrib":self.Attrib.ToDic(),"Dic":self.Dictionary}
        
    def FromDic(self,dic):
        
        #loggin.info("@Sheet.FromDic()")

        for key in dic:
            if dic[key]=="None":
                dic[key]=None
        
        self.Features=[]
        if dic["TYP"]=="Sheet":
            for i,item in enumerate(dic["Features"]):
                self.Features.append(Feature().FromDic(item))
            self.Attrib=Attrib().FromDic(dic["Attrib"])
            self.Dictionary=dic["Dic"]
            
        return self
        
        
class Product(Archive):
    
    def __init__(self,attrib=None,feature=None,context=None,dic=None,products=None,profiles=None,sheets=None,parts=None):
        
        #loggin.info("@Product.__init__()")

        self.Context=context
        self.Error=""
        self.Attrib=attrib
        #self.CustomAttrib=None

        if feature==None:
            self.Features=[] #KEF auf 0
        else:
            self.Features=[feature]
        if dic==None:
            dic={}
        self.Dictionary=dic
        
        if products==None:
            self.Products=[]
        else:
            self.Products=products

        if profiles==None:
            self.Profiles=[]
        else:
            self.Profiles=profiles
        
        if sheets==None:
            self.Sheets=[]
        else:
            self.Sheets=sheets
            
        if parts==None:
            self.Parts=[]
        else:
            self.Parts=parts
        
    def __str__(self):
        
        #loggin.info("@Product.__str__()")

        string="Product-Instance:\n"
        string+=str(self.Attrib)+"\n"
        
        string+="self.Features:\n"
        for feat in self.Features:
            string+=str(feat)+"\n"
        string+="self.Products:\n"
        for prod in self.Products:
            string+=str(prod)+"\n"
        string+="self.Profiles:\n"
        for prof in self.Profiles:
            string+=str(prof)+"\n"
        string+="self.Sheets:\n"
        for sheet in self.Sheets:
            string+=str(sheet)+"\n"
        string+="self.Parts:\n"
        for part in self.Parts:
            string+=str(part)+"\n"
        
        return string
                
    def Breps(self):
        
        #loggin.info("@Product.Breps()")

        breps=[]
        for p in self.Products:
            breps+=p.Breps()       
        for b in self.Profiles:
            res=b.Brep()
            if res!=None:
                breps.append(res)
        for s in self.Sheets:
            res=s.Brep()
            if res!=None:
                breps.append(res)
        for p in self.Parts:
            res=p.Brep()
            if res!=None:
                breps.append(res)
            
        return breps
        
    def Weight(self):
        
        #loggin.info("@Product.Weight()")

        weight=0
        for p in self.Products:
            weight+= p.Weight()
        for b in self.Profiles:
            weight+= b.Weight()
        for s in self.Sheets:
            weight+= s.Weight()
        for p in self.Parts:
            weight+= p.Weight()
        
        if weight!=0:
            return weight
        else:
            return self.Features[0].Weight
        
    def BoundingBox(self,plane=None,getbox=False):
        
        #loggin.info("@Product.BoundingBox()")

        breps=self.Breps()
        if breps!=[]:
            if plane==None:
                plane=Rhino.Geometry.Plane(self.Features[0].Plane)            
                
            bbx=breps[0].GetBoundingBox(plane)
            for i in range(1,len(breps)):
                bbx.Union(breps[i].GetBoundingBox(plane))
            
            if not getbox:
                return bbx.Diagonal.X,bbx.Diagonal.Y,bbx.Diagonal.Z
            else:
                if plane!=None:
                    xform2=Rhino.Geometry.Transform.ChangeBasis(plane,Rhino.Geometry.Plane.WorldXY)
                    return Rhino.Geometry.Box(plane,bbx)
                else:
                    xform2=Rhino.Geometry.Transform.ChangeBasis(self.Features[0].Plane,Rhino.Geometry.Plane.WorldXY)
                    return Rhino.Geometry.Box(self.Features[0].Plane,bbx)
                    
        else: return self.Features[0].SizeX,self.Features[0].SizeY,self.Features[0].SizeZ
        
    def UpdateObjectProperties(self):  
    
        #loggin.info("@Product.UpdateObjectProperties()")

        for p in self.Products:
            p.UpdateObjectProperties()
        for b in self.Profiles:
            b.UpdateObjectProperties()
        for s in self.Sheets:
            s.UpdateObjectProperties()
        for p in self.Parts:
            p.UpdateObjectProperties()

        self.Features[0].Weight=self.Weight()
        self.Features[0].SizeX,self.Features[0].SizeY,self.Features[0].SizeZ=self.BoundingBox()
        self.Features[0].UpdateDimension()
        self.Features[0].UpdateArea()

        return True
    
    def ApplyFeatures(self,tolerance):
        
        #loggin.info("@Product.ApplyFeatures()")

        for p in self.Products:
            p.ApplyFeatures(tolerance)
        for b in self.Profiles:
            b.ApplyFeatures(tolerance)
        for s in self.Sheets:
            s.ApplyFeatures(tolerance)
        for p in self.Parts:
            p.ApplyFeatures(tolerance)
        
        return True
        
    def Copy(self,plane=None,subelements=False):
        
        #loggin.info("@Product.Copy()")

        newproduct=Product(attrib=self.Attrib.Copy(),feature=self.Features[0].Copy(),dic=copy.deepcopy(self.Dictionary))
        for i in range(1,len(self.Features)):
            newproduct.Features.append(self.Features[i].Copy())
            
        if subelements:
            for p in self.Products:
                newproduct.Products.append(p.Copy(subelements=subelements))
            for b in self.Profiles:
                newproduct.Profiles.append(b.Copy())
            for s in self.Sheets:
                newproduct.Sheets.append(s.Copy())
            for p in self.Parts:
                newproduct.Parts.append(p.Copy())
            
        if plane!=None:
            newproduct.Orient(plane)
        
        return newproduct 
        
    def Orient(self,planeto,planefrom=None):
        
        #loggin.info("@Product.Orient()")

        if planefrom==None:
            planefrom=Rhino.Geometry.Plane(self.Features[0].Plane)
        for i in range(0,len(self.Features)):
            self.Features[i].Orient(planeto=planeto,planefrom=planefrom)
        
        for p in self.Products:
            p.Orient(planeto,planefrom)
        for b in self.Profiles:
            b.Orient(planeto,planefrom)
        for s in self.Sheets:
            s.Orient(planeto,planefrom)
        for p in self.Parts:
            p.Orient(planeto,planefrom)

        return True
    
    def Show(self,context,group=None,block=False,depth=0,id=None,lod=500,writeattribtoobject=False,extraguids=None,path_attrib_key_map="",path_feat_key_map="",path_attrib_fin_map=""):
        
        #loggin.info("@Product.Show()")

        if id==None:
            id=self.Attrib.ID
        
        #print depth
        #print self.Attrib.Prefix+"-"
        bli=None
        parts=[]
        for p in self.Products:
            if p.Features[0].LOD<=lod:
                res=p.Show(context=context,group=group,block=block,depth=depth+1,id=id,lod=lod,writeattribtoobject=writeattribtoobject,path_attrib_key_map=path_attrib_key_map,path_feat_key_map=path_feat_key_map,path_attrib_fin_map=path_attrib_fin_map)
                if res!=None:
                    parts.extend(res)
                        
        for b in self.Profiles:
            if b.Features[0].LOD<=lod:
                res=b.Show(context=context,group=group,block=block,writeattribtoobject=writeattribtoobject,path_attrib_key_map=path_attrib_key_map,path_feat_key_map=path_feat_key_map,path_attrib_fin_map=path_attrib_fin_map)
                if res!=None:
                    parts.append(res)
                        
        for s in self.Sheets:
            if s.Features[0].LOD<=lod:
                res=s.Show(context=context,group=group,block=block,writeattribtoobject=writeattribtoobject,path_attrib_key_map=path_attrib_key_map,path_feat_key_map=path_feat_key_map,path_attrib_fin_map=path_attrib_fin_map)
                if res!=None:
                    parts.append(res)
                        
        for p in self.Parts:
            if p.Features[0].LOD<=lod:
                res=p.Show(context=context,group=group,block=block,writeattribtoobject=writeattribtoobject,path_attrib_key_map=path_attrib_key_map,path_feat_key_map=path_feat_key_map,path_attrib_fin_map=path_attrib_fin_map)
                if res!=None:
                    parts.append(res)
        
        if extraguids!=None:
            parts+=extraguids
            
        if block:
            if self.Attrib.Block==True:

                dot=True
                if self.Attrib.ID=="":
                    dot=False
                    self.Attrib.ID="1"
                bln=self.Attrib.PosNo()
                if bln in rs.BlockNames():
                    cn=1
                    if dot:
                        while bln+"."+str(cn) in rs.BlockNames():
                            cn+=1
                        bln+="."+str(cn)
                    else:
                        while bln in rs.BlockNames():
                            cn+=1
                            self.Attrib.ID=str(cn)
                            bln=self.Attrib.PosNo()
                    
                if len(parts)>0:
                    bl=rs.AddBlock(parts,[0,0,0],bln,True)
                    if bl!=None:
                        rs.DeleteObjects(parts)
                        bli=rs.InsertBlock(bl,[0,0,0])
                        rs.AddLayer(self.Features[0].Layer)
                        rs.ObjectLayer(bli,self.Features[0].Layer)

                        if writeattribtoobject:
                            self.UpdateObjectProperties()
                            dicx=self.Attrib.ToDic2(path_key_map=path_attrib_key_map,path_fin_map=path_attrib_fin_map)
                            dicx.update(self.Features[0].ToDic2(path_key_map=path_feat_key_map))
                            self.WriteObjAttrib(bli,dicx)

                        return [bli]     
            else:   
                if len(parts)>0:
                    return parts
        else:
            if len(parts)>0:
                return parts
                         
        return None
    
    def ToAPArtikel(self,struktur=0,menge=None):
        
        #loggin.info("@Product.ToAPArtikel()")

        self.UpdateObjectProperties()  
        
        apa=APArtikel()
        apa.VBME=self.Attrib.VBME
        #self.LFDNR=lfdnr
        apa.Struktur=struktur
        apa.Artikel=self.Attrib.APVorlage
        apa.Name2=self.Attrib.ZusatzText 
        if menge==None:
            apa.Menge=self.Attrib.Menge
        else:
            apa.Menge=menge
        apa.ME="Stück"
        apa.Laenge=self.Features[0].SizeX
        apa.Breite=self.Features[0].SizeY
        apa.Hoehe=self.Features[0].SizeZ
        #apa.Staerke=staerke
        apa.Gewicht=self.Features[0].Weight
        #apa.Material=material
        #apa.Zeichnung=zeichnung
        apa.ZeichnungPos=self.Attrib.PosNo()
        apa.ZText=self.Attrib.TextPos
        #apa.HerstStueli=herststueli
        apa.Einkauf=self.Attrib.Einkauf
        apa.Fertigung=self.Attrib.Fertigung
        apa.Auftrag=self.Attrib.Auftrag
        apa.Lager=self.Attrib.Lager
        #apa.Beistellung=beistellung
        #apa.Fremdmontage=fremdmontage
        apa.FinishCode=self.Attrib.FinishCode
        apa.MatCode=self.Attrib.MatCode
        apa.RawMat=self.Attrib.RawMat
        apa.UnrolX=self.Features[0].UnrolX
        apa.UnrolY=self.Features[0].UnrolY
        apa.UnrolZ=self.Features[0].UnrolZ
        
        for p in self._StripDup(self.Products):
            res=p[0].ToAPArtikel(struktur+1,menge=p[1])
            if res!=None:
                apa.Children.append(res)
        for b in self._StripDup(self.Profiles):
            res=b[0].ToAPArtikel(struktur+1,menge=b[1])
            if res!=None:
                apa.Children.append(res)
        for s in self._StripDup(self.Sheets):
            res=s[0].ToAPArtikel(struktur+1,menge=s[1])
            if res!=None:
                apa.Children.append(res)
        for p in self._StripDup(self.Parts):
            res=p[0].ToAPArtikel(struktur+1,menge=p[1])
            if res!=None:
                apa.Children.append(res)
        
        return apa
        
    def ToDic(self,savebreps=False,context=None):

        #loggin.info("@Product.ToDic()")

        self.UpdateObjectProperties()
        return {
        "TYP":"Product",
        "Features":[x.ToDic(savebreps,context) for x in self.Features],
        "Attrib":self.Attrib.ToDic(),
        "Dic":self.Dictionary,
        "Products":[x.ToDic(savebreps,context) for x in self.Products],
        "Profiles":[x.ToDic(savebreps,context) for x in self.Profiles],
        "Sheets":[x.ToDic(savebreps,context) for x in self.Sheets],
        "Parts":[x.ToDic(savebreps,context) for x in self.Parts]
        }
    
    def ToNCCollection(self,vis=True,filename="collection",parentlayer=""):
        
        #loggin.info("@Product.ToNCCollection()")

        #nccol=NCCollection(filename)
        #for b in self.Profiles:
        #    nccol.Add(b.ToNCItem(vis=vis,parentlayer=parentlayer))
        
        nccols={}
        for b in self.Profiles:
            nci=b.ToNCItem(vis=vis,parentlayer=parentlayer)
            id=b.Attrib.RawMat
            if id in nccols:
                nccols[id].Add(nci)
            else:
                nccols[id]=NCCollection(filename + "-" + id)
                nccols[id].Add(nci)
                
        #nccol.ExportCSV(path)
        return nccols 
    
    def FromDic(self,dic):

        #loggin.info("@Product.FromDic()")

        for key in dic:
            if dic[key]=="None":
                dic[key]=None        
        
        if dic["TYP"]=="Product":
            if len(dic["Features"])>0:
                for i,item in enumerate(dic["Features"]):
                    self.Features.append(Feature().FromDic(item))
            if len(dic["Products"])>0:
                for i,item in enumerate(dic["Products"]):
                    self.Products.append(Product().FromDic(item))
            if len(dic["Profiles"])>0:
                for i,item in enumerate(dic["Profiles"]):
                    self.Profiles.append(Profile().FromDic(item))
            if len(dic["Sheets"])>0:
                for i,item in enumerate(dic["Sheets"]):
                    self.Sheets.append(Sheet().FromDic(item))
            if len(dic["Parts"])>0:
                for i,item in enumerate(dic["Parts"]):
                    self.Parts.append(Part().FromDic(item))
            
            self.Attrib=Attrib().FromDic(dic["Attrib"])
            self.Dictionary=dic["Dic"]
            
        return self
        
    def LoadFromFile(self,files,id=0):
        
        #loggin.info("@Product.LoadFromFile()")

        for file in files:
            rs.Command("-_import " + file.Path + " _enter")
            lco=rs.LastCreatedObjects()
            brep=rs.coercebrep(lco[id])
            part=Part(attrib=file.Attrib,feature=file.Feature)
            self.Parts.append(part)
            if isinstance(brep,Rhino.Geometry.Brep):
                part.Features[0].Brep=brep
                rs.DeleteObjects(lco)
            else:
                part.Features[0].ObjectID=lco[id]
                
        return None
    
    def DeleteParts(self,ids):
        
        #loggin.info("@Product.DeleteParts()")

        np=[]
        for i in range(0,len(self.Parts)):
            if not i in ids:
                np.append(self.Parts[i])
            else:
                if self.Parts[i].Features[0].ObjectID!=None:
                    rs.DeleteObject(self.Parts[i].Features[0].ObjectID)
        
        self.Parts=np
        
        return None
    
    def CleanUp(self):
        
        #loggin.info("@Product.CleanUp()")

        for p in self.Products:
            p.CleanUp()
        for b in self.Profiles:
            b.CleanUp()
        for s in self.Sheets:
            s.CleanUp()
        for p in self.Parts:
            p.CleanUp()
        for f in self.Features:
            f.CleanUp()
            
        return None
    
    def Export(self):

        #loggin.info("@Product.Export()")

        pass
    
    def _StripDup(self, list):
        
        #loggin.info("@Product._StripDup()")

        dic={}
        for entry in list:
            pos=entry.Attrib.PosNo()
            if pos in dic:
                dic[pos].append(entry)
            else:
                dic[pos]=[entry]
        
        striplist=[]
        for key in dic:
            striplist.append((dic[key][0],len(dic[key])))
        
        return striplist
    
###hier rework noetig ---> Geo Handling extra Klasse ###
class ProfileAxis:
    
    def __init__(self,basecrv=None,reference=None,refsrf=None,optimize=0,stsize=50,revpoint=None,tolerance=3,vmean=None,offset=0,oripoint=None,extend_srf=500.):
        
        #loggin.info("@ProfileAxis.__init__()")

        if vmean!=None:
            vmean.Unitize()
            
        if reference!=None:
            if not isinstance(reference,Rhino.Geometry.Curve):
                self.RefCrv=rs.coercecurve(reference)
            else:
                self.RefCrv=reference
        if basecrv!=None:
            self.BaseCrv=self.ProfileCurve(basecrv)
        self.ApproxCrvs=[self.ProfileCurve()]
        self.RevPoint=revpoint
        self.OriPoint=oripoint
        self.Tags=self._Tags()
        
        if (basecrv==None) and (reference!=None) and (refsrf!=None) and (optimize in [0,1]):
            points=rs.DivideCurve(reference,int(rs.CurveLength(reference)/stsize))
            
            vx=points[len(points)-1]-points[0]
            #vm=Rhino.Geometry.Vector3d(0,0,0)
            newpoints=[]
            normals=[]
            planes=[]
            for point in points:
                if isinstance(refsrf,list):
                    rsrf=rs.PointClosestObject(point,refsrf)[0]
                else:
                    rsrf=refsrf
                vn=rs.SurfaceNormal(rsrf,rs.SurfaceClosestPoint(rsrf,point))
                normals.append(vn)
                if vmean!=None:
                    newpoints.append(point+vmean*offset)                
                else:
                    newpoints.append(point+vn*offset)
                planes.append(Rhino.Geometry.Plane(newpoints[-1],vn))
            
            vm=self._BuildBestMean(planes)
            vm.Unitize()
            if vmean!=None:
                vm=vmean
            
            #rs.AddPoints(newpoints)
            self.BaseCrv= self.ProfileCurve(Rhino.Geometry.NurbsCurve.CreateControlPointCurve(newpoints))
            #sc.doc.Objects.AddCurve(self.BaseCrv.Base)
            
            self.ApproxCrvs=[self.ProfileCurve()]
            self.ApproxCrvs[0].VMeanX=vm
            if optimize==1:
                #rs.AddPlaneSurface(Rhino.Geometry.Plane(points[0],vx,vm),2000,2000)
                self.ApproxArcs(Rhino.Geometry.Plane(points[0],vx,vm),newpoints,tolerance,extend_srf=extend_srf,revpoint=revpoint)
                if self.ApproxCrvs[0].DevX>20 or self.ApproxCrvs[0].DevY>20:
                    self.ApproxSpline(normals,newpoints,tolerance)    
                    rs.AddTextDot("opt. failed",points[10]) 

            if self.ApproxCrvs[0].Base==None:
                optimize=0
            if optimize==0:
                self.ApproxSpline(normals,newpoints,tolerance,extend_srf=extend_srf)
                
            if revpoint!=None:
                if revpoint.DistanceTo(self.ApproxCrvs[0].Base.PointAtStart)>revpoint.DistanceTo(self.ApproxCrvs[0].Base.PointAtEnd):
                    self.ApproxCrvs[0].Base.Reverse()
                
    def ApproxArcs(self,plane,grevillepoints,tolerance=5,extend_srf=500.,revpoint=None):

        #loggin.info("@ProfileAxis.ApproxArcs()")             

        self.BaseCrv.PlaneX=plane
        self.BaseCrv.PlaneY=Rhino.Geometry.Plane(plane.Origin,plane.XAxis,plane.ZAxis)
        
        #rs.AddPlaneSurface(self.BaseCrv.PlaneX,200,200)
        #rs.AddPlaneSurface(self.BaseCrv.PlaneY,200,200)
        
        
        newpx=[self.BaseCrv.PlaneX.ClosestPoint(x) for x in grevillepoints]
        newpy=[self.BaseCrv.PlaneY.ClosestPoint(x) for x in grevillepoints]
        
        self.BaseCrv.ProjectX=Rhino.Geometry.NurbsCurve.CreateControlPointCurve(newpx)
        self.BaseCrv.ProjectY=Rhino.Geometry.NurbsCurve.CreateControlPointCurve(newpy)
        
        for i,crv in enumerate([self.BaseCrv.ProjectX,self.BaseCrv.ProjectY],0):
            crvres,dev,tag=self._SplineToLine(crv)
            if dev>tolerance:
                crvres,dev,tag=self._SplineToArc(crv)
            if dev>tolerance:
                crvres,dev,tag=self._PlanarSplineToBiarc(crv)

                        
            #if revpoint!=None:
            #   if revpoint.DistanceTo(crvres.PointAtStart)>revpoint.DistanceTo(crvres.PointAtEnd):
            #        crvres.Reverse()

            if i==0:
                self.ApproxCrvs[0].ProjectX=crvres
                self.ApproxCrvs[0].TagX=tag
                self.ApproxCrvs[0].DevX=dev
                self.ApproxCrvs[0].PlaneX=self.BaseCrv.PlaneX
            else:
                self.ApproxCrvs[0].ProjectY=crvres
                self.ApproxCrvs[0].TagY=tag
                self.ApproxCrvs[0].DevY=dev
                self.ApproxCrvs[0].PlaneY=self.BaseCrv.PlaneY

        self.ApproxCrvs[0].SurfaceX = Rhino.Geometry.Surface.CreateExtrusion(self.ApproxCrvs[0].ProjectX, self.ApproxCrvs[0].PlaneX.ZAxis*(extend_srf*2))
        vtrans=self.ApproxCrvs[0].PlaneX.ZAxis*-extend_srf
        transx=Rhino.Geometry.Transform.Translation(vtrans.X,vtrans.Y,vtrans.Z)
        self.ApproxCrvs[0].SurfaceX.Transform(transx)
        self.ApproxCrvs[0].SurfaceY = Rhino.Geometry.Surface.CreateExtrusion(self.ApproxCrvs[0].ProjectY, self.ApproxCrvs[0].PlaneY.ZAxis*(extend_srf*2))
        vtrans=self.ApproxCrvs[0].PlaneY.ZAxis*-extend_srf
        transy=Rhino.Geometry.Transform.Translation(vtrans.X,vtrans.Y,vtrans.Z)
        self.ApproxCrvs[0].SurfaceY.Transform(transy)
        intcrvs=Rhino.Geometry.Intersect.Intersection.SurfaceSurface(self.ApproxCrvs[0].SurfaceX,self.ApproxCrvs[0].SurfaceY,sc.doc.ModelAbsoluteTolerance)
        if intcrvs[0]!=True:
            return None
        if len(intcrvs[1])>1:
            print "multiple intersection results!"
            return None
        self.ApproxCrvs[0].Base=intcrvs[1][0]
        
        return self.ApproxCrvs[0]

    def ApproxSpline(self,vectors,grevillepoints,tolerance=5,extend_srf=500.):
           
        #loggin.info("@ProfileAxis.ApproxSpline()")

        crvsx=[]
        pstart=[]
        pend=[]
        for i,p in enumerate(grevillepoints,0):
             pstart.append(p+vectors[i]*extend_srf)
             pend.append(p-vectors[i]*extend_srf)
             lc=Rhino.Geometry.LineCurve(pstart[i],pend[i])
             crvsx.append(lc)
        crvsx.append(Rhino.Geometry.NurbsCurve.CreateInterpolatedCurve(pstart,3))
        crvsx.append(Rhino.Geometry.NurbsCurve.CreateInterpolatedCurve(pend,3))
        

        crvsy=[]
        pstart=[]
        pend=[]
        for i,p in enumerate(grevillepoints,0):
             tan=self.BaseCrv.Base.TangentAt(self.BaseCrv.Base.ClosestPoint(p)[1])
             v=rs.VectorCrossProduct(tan,vectors[i])
             pstart.append(p+v*extend_srf)
             pend.append(p-v*extend_srf)
             lc=Rhino.Geometry.LineCurve(pstart[i],pend[i])
             crvsy.append(lc)
        crvsy.append(Rhino.Geometry.NurbsCurve.CreateInterpolatedCurve(pstart,3))
        crvsy.append(Rhino.Geometry.NurbsCurve.CreateInterpolatedCurve(pend,3))
        
        # for curve in crvsy+crvsx:
        #     sc.doc.Objects.AddCurve(curve)
        
        self.ApproxCrvs[0].SurfaceY = Rhino.Geometry.NurbsSurface.CreateNetworkSurface(crvsx,0,0.01,0.01,sc.doc.ModelAngleToleranceDegrees)[0]
        self.ApproxCrvs[0].SurfaceX = Rhino.Geometry.NurbsSurface.CreateNetworkSurface(crvsy,0,0.01,0.01,sc.doc.ModelAngleToleranceDegrees)[0]
        self.ApproxCrvs[0].TagY = self.Tags.Spline
        self.ApproxCrvs[0].TagX = self.Tags.Spline
        
        #sc.doc.Objects.AddSurface(self.ApproxCrvs[0].SurfaceY)
        #sc.doc.Objects.AddSurface(self.ApproxCrvs[0].SurfaceX)
        

        intcrvs=Rhino.Geometry.Intersect.Intersection.SurfaceSurface(self.ApproxCrvs[0].SurfaceX,self.ApproxCrvs[0].SurfaceY,sc.doc.ModelAbsoluteTolerance)
        if intcrvs[0]!=True:
            return None
        if len(intcrvs[1])>1:
            print "multiple intersection results!"
            return None
        self.ApproxCrvs[0].Base=intcrvs[1][0]
        #sc.doc.Objects.AddCurve(self.ApproxCrvs[0].Base)
        
        return self.ApproxCrvs[0]

    def _SplineToLine(self,spline,tol=10,div=40):
        # Gen min. dev. Line
        
        #loggin.info("@ProfileAxis._SplineToLine()")

        p0=spline.PointAtStart
        p1=spline.PointAtEnd
        vx=p1-p0
        vx.Unitize()
        line=Rhino.Geometry.Line(p0,p1)
        
        devs=[]
        divdev=int(line.Length/tol)
        step=line.Length/divdev
        for count in range(0,divdev+1):
            linept=p0+vx*step*count
            dev=linept.DistanceTo(spline.PointAt(spline.ClosestPoint(linept)[1]))
            devs.append(dev)
        
        #sc.doc.Objects.AddLine(line)
        #print max(devs)
        return Rhino.Geometry.LineCurve(line),max(devs),self.Tags.Line

    def _SplineToArc(self,spline,tol=10,div=40):
        # Gen min. dev. Arc
        
        #loggin.info("@ProfileAxis._SplineToArc()")

        dom=spline.Domain
        stepspline=(dom.T1-dom.T0)/div
        p0=spline.PointAtStart
        p1=spline.PointAtEnd
        
        ###########################################################################
        #Loop to find best theta1&2
        devmax=1000000
        bestarc=None
        
        for i in range(1,div):
            
            ponarc=spline.PointAt(dom.T0+stepspline*i) 
            arc=Rhino.Geometry.Arc(p0,ponarc,p1)
            
            devs=[]
            dom=arc.AngleDomain
            divdev=int(arc.Length/tol)
            step=(dom.T1-dom.T0)/divdev
            for count in range(0,divdev+1):
                arcpt=arc.PointAt(count*step)
                dev=arcpt.DistanceTo(spline.PointAt(spline.ClosestPoint(arcpt)[1]))
                devs.append(dev)
                  
            #print max(devs)
            if max(devs)<devmax:
                bestarc=arc
                devmax=max(devs)
            
            ###########################################################################
        #sc.doc.Objects.AddArc(bestarc)
            
        return Rhino.Geometry.ArcCurve(bestarc),devmax,self.Tags.Arc

    def _PlanarSplineToBiarc(self,spline,tol=10,div=40):
        #implementation of 
        # Gen min. dev. Biarc
        
        #loggin.info("@ProfileAxis._PlanarSplineToBiarc()")

        dom=spline.Domain
        p0=spline.PointAtStart
        p1=spline.PointAtEnd
        t0=spline.TangentAtStart
        t1=spline.TangentAtEnd
            
        c=Rhino.Geometry.Line(p0,p1)
        C=rs.LineLineIntersection(Rhino.Geometry.Line(p0,p0+t0),Rhino.Geometry.Line(p1,p1+t1))
        if C==None:
            return None
        else:
            C=C[0]
        a=Rhino.Geometry.Line(p0,C)
        b=Rhino.Geometry.Line(p1,C)
    
        #assuming curve is planar
        res,frame=spline.FrameAt(dom.T0)
        planeorigin=c.From+c.Direction/2
        plane=Rhino.Geometry.Plane(planeorigin,c.Direction,frame.YAxis*-1)
        acircle=Rhino.Geometry.Circle(p0,p1,C)
        phi=acircle.Radius
        
        #rs.AddPlaneSurface(plane,500,200)
        alpha=rs.VectorAngle(c.Direction,a.Direction)
        beta=rs.VectorAngle(c.Direction*-1,b.Direction)
        delta=(beta-alpha)/2
        
        #print R
        R=c.Length/(2*math.sin(math.radians((alpha+beta)/2)))
        r=(b.Length-a.Length)/2
        
        d=2*phi*math.cos(math.radians(beta))
        e=2*phi*math.cos(math.radians(alpha))
        
        xd=d*math.sin(math.radians(alpha))-c.Length/2
        yd=-d*math.cos(math.radians(alpha))
        D=rs.XformCPlaneToWorld(Rhino.Geometry.Point3d(xd,yd,0),plane)
        xi=0
        yi=-R*math.cos(math.radians((alpha+beta)/2))
        I=rs.XformCPlaneToWorld(Rhino.Geometry.Point3d(xi,yi,0),plane)
        
        """
        VIZ for DEBUG
        rs.AddPoint(I)
        rs.AddPoint(D)
        sc.doc.Objects.AddCircle(Rhino.Geometry.Circle(p0,p1,D))
        plane.Origin=I
        sc.doc.Objects.AddCircle(Rhino.Geometry.Circle(plane,r))
        plane.Origin=planeorigin
        rs.AddLine(p0,D)
        rs.AddLine(p1,D)
        """
        
        ###########################################################################
        #Loop to find best theta1&2
        devmax=1000000
        bestbiarc=None
        
        for i in range(1,div):
    
            if delta>=0:
                step=(2*alpha)/div
                theta1=0+step*i
            if delta<0:
                step=((alpha+beta)-(alpha-beta))/div
                theta1=(alpha-beta)+step*i
            theta2=alpha+beta-theta1
            
            #print str(theta1) +" --- " +str(theta2) 
            
            R1=(R*math.sin(math.radians(theta1/2+delta)))/math.sin(math.radians(theta1/2))
            R2=(R*math.sin(math.radians(theta2/2-delta)))/math.sin(math.radians(theta2/2))
            
            plane.Origin=planeorigin
            p0lok=rs.XformWorldToCPlane(p0,plane)
            p1lok=rs.XformWorldToCPlane(p1,plane)
            
            xa=p0lok.X
            ya=p0lok.Y
            xb=p1lok.X
            yb=p1lok.Y
        
            xc1=xa+(R1/d)*(xd-xa)
            yc1=ya+(R1/d)*(yd-ya)
            
            xc2=xb+(R2/e)*(xd-xb)
            yc2=yb+(R2/e)*(yd-yb)
            
            C1glob=rs.XformCPlaneToWorld(Rhino.Geometry.Point3d(xc1,yc1,0),plane)
            C2glob=rs.XformCPlaneToWorld(Rhino.Geometry.Point3d(xc2,yc2,0),plane)
            
            #polycurve aus beiden arcs bauen
            c1c2=Rhino.Geometry.Line(C1glob,C2glob)
            plane.Origin=I
            tcircle=Rhino.Geometry.Circle(plane,R)
            plane.Origin=planeorigin
            T=Rhino.Geometry.Intersect.Intersection.LineCircle(c1c2,tcircle)
            if T[2].DistanceTo(planeorigin)<T[4].DistanceTo(planeorigin):
                T=T[2]
            else:
                T=T[4]
            
            v1=p0-C1glob
            v2=T-C1glob
            v=v1+v2
            v.Unitize()
            ponarc1=C1glob+v*R1
            arc1=Rhino.Geometry.Arc(p0,ponarc1,T)
            
            v1=p1-C2glob
            v2=T-C2glob
            v=v1+v2
            v.Unitize()
            ponarc2=C2glob+v*R2
            arc2=Rhino.Geometry.Arc(T,ponarc2,p1)
    
            biarc=Rhino.Geometry.PolyCurve()
            biarc.Append(arc1)
            biarc.Append(arc2)
            
            #sc.doc.Objects.AddCurve(biarc)
            
            devs=[]
            for arc in [arc1,arc2]:
                dom=arc.AngleDomain
                divdev=int(arc.Length/tol)
                if divdev==0:
                    divdev=2
                step=(dom.T1-dom.T0)/divdev
                for count in range(0,divdev+1):
                    arcpt=arc.PointAt(count*step)
                    dev=arcpt.DistanceTo(spline.PointAt(spline.ClosestPoint(arcpt)[1]))
                    devs.append(dev)
                  
            #print max(devs)
            if max(devs)<devmax:
                bestbiarc=biarc
                devmax=max(devs)
            
            #VIZ for DEBUG
            #sc.doc.Objects.AddCircle(tcircle)
            #sc.doc.Objects.AddArc(arc1)
            #sc.doc.Objects.AddArc(arc2)
            #rs.AddPoint(T)
            #sc.doc.Objects.AddCurve(biarc)
            
            ###########################################################################
        
        #sc.doc.Objects.AddCurve(bestbiarc)
        #print devmax
        
        #VIZ for DEBUG
        #linec1c2=Rhino.Geometry.Line(bestarc1[0],bestarc2[0])
        #pt=Rhino.Geometry.Intersect.Intersection.LineCircle(linec1c2,tcircle)
        ##sc.doc.Objects.AddCircle(tcircle)
        #rs.AddLine(pt[2],pt[4])
        ##rs.AddLine(C1glob,C2glob)
        #plane.Origin=bestarc1[0]
        #rs.ObjectColor(rs.AddCircle(plane,bestarc1[1]),[255,0,0])    
        #plane.Origin=bestarc2[0]
        #rs.ObjectColor(rs.AddCircle(plane,bestarc2[1]),[255,0,0])
        
        
        return bestbiarc,devmax,self.Tags.Biarc


    def _BuildBestMean(self,planes):

        vs=[pl.ZAxis for pl in planes]
        pls=planes[:]
        angles=[]

        for i,pl in enumerate(pls):
            angles_=[]
            ratios_=[]
            range_=[]
            for j,v in enumerate(vs):
                if j!=i:
                    cp=rs.PlaneClosestPoint(pls[j],pls[j].Origin+vs[i])
                    #if rs.VectorAngle(vs[i],vs[j])>0:
                    v_=rs.PlaneClosestPoint(pls[j],pls[j].Origin+vs[i])-pls[j].Origin
                    if v_.Length>0.:
                        angle_=rs.VectorAngle(vs[j],v_)
                        angles_.append(angle_)
            
            if len(angles_)==0:
                return vs[0]
            angles.append(max(angles_))
        
        min_=min(angles)
        min_index=angles.index(min_)
        
        #rs.AddLine(pls[min_index].Origin,pls[min_index].Origin+vs[min_index]*500)
        #app_dev=500*math.sin(math.radians(min_))
        #td=rs.AddTextDot("{0:.2f} \n=> approx. dev.: {1:.2f}mm/500 p-depth ".format(min(angles),app_dev),pls[min_index].Origin)
        #if app_dev>10:
        #    rs.ObjectColor(td,[255,0,0])
        return vs[min_index]


    def FrameAt(self,point):
        
        #loggin.info("@ProfileAxis.FrameAt()")

        if len(self.ApproxCrvs)==1:
            t=self.ApproxCrvs[0].Base.ClosestPoint(point)
            return Rhino.Geometry.Plane(self.ApproxCrvs[0].Base.PointAt(t),self.ApproxCrvs[0].Base.TangentAt(t)) 
        else:
            res,t1=self.ApproxCrvs[0].Base.ClosestPoint(point)
            p1=self.ApproxCrvs[0].Base.PointAt(t1)
            res,t2=self.ApproxCrvs[1].Base.ClosestPoint(p1)
            p2=self.ApproxCrvs[1].Base.PointAt(t2)
            
            vx=p2-p1
            vy=rs.VectorCrossProduct(vx,self.ApproxCrvs[0].Base.TangentAt(t1))*-1
            
        return Rhino.Geometry.Plane(p1,vx,vy)
        
    class _Tags:
        
        def __init__(self):

            #loggin.info("@ProfileAxis._Tags.__init__()")

            self.Line="line"
            self.Arc="arc"
            self.Biarc="biarc"
            self.Spline="spline"
            
        def Zip(self):    

            #loggin.info("@ProfileAxis._Tags.Zip()")

            return [self.Line,self.Arc,self.Biarc]
            
    class ProfileCurve:
        
        def __init__(self,curve=None):

            #loggin.info("@ProfileAxis.ProfileCurve.__init__()")

            self.Layer=""
            self.Base=curve
            self.VMeanX=None
            self.VMeanY=None
            self.ProjectX=None
            self.ProjectY=None
            self.TagX=None
            self.TagY=None
            self.DevX=None
            self.DevY=None
            self.PlaneX=None
            self.PlaneY=None
            self.SurfaceX=None
            self.SurfaceY=None
        
        def Extend(self,val=None,ptstart=None,ptend=None,style=None):
            
            if style==None:
                style=Rhino.Geometry.CurveExtensionStyle.Smooth

            #loggin.info("@ProfileAxis.ProfileCurve.Extend()")

            extendcurve=ProfileAxis().ApproxCrvs[0]
            
            crvex=None
            if val!=None:
                crvex=self.Base.Extend(Rhino.Geometry.CurveEnd.Both,val,style)
            if ptstart!=None:
                if crvex!=None:
                    crvex=crvex.Extend(Rhino.Geometry.CurveEnd.Start,style,ptstart)
                else:
                    crvex=self.Base.Extend(Rhino.Geometry.CurveEnd.Start,style,ptstart)
            if ptend!=None:
                if crvex!=None:
                    crvex=crvex.Extend(Rhino.Geometry.CurveEnd.End,style,ptend)
                else:
                    crvex=self.Base.Extend(Rhino.Geometry.CurveEnd.Start,style,ptend)
            
            extendcurve.Base=crvex
            
            return extendcurve.Base
        
        def Offset(self,offsetx=None,offsety=None,revpoint=None,rebuild=True,spacing=50):
            
            if offsetx==0 or offsetx==0.:
                offsetx=None
            if offsety==0 or offsety==0.:
                offsety=None

            #loggin.info("@ProfileAxis.ProfileCurve.Offset()")

            offsetcurve=ProfileAxis().ProfileCurve()
            
            #NOTE::
            #übergebene Normalenrichtung wird nicht geändert und bleibt beim offset erhalten
            if offsetx!=None:
                offsetcurve.SurfaceX=self.SurfaceX.Offset(offsetx,sc.doc.ModelAbsoluteTolerance)
                offsetcurve.ProjectX=self.ProjectX.Offset(self.PlaneX,-offsetx,sc.doc.ModelAbsoluteTolerance,Rhino.Geometry.CurveOffsetCornerStyle.Smooth)
            else:
                offsetcurve.SurfaceX=self.SurfaceX
                offsetcurve.ProjectX=[self.ProjectX]
            
            if offsety!=None:
                offsetcurve.SurfaceY=self.SurfaceY.Offset(offsety,sc.doc.ModelAbsoluteTolerance)
                offsetcurve.ProjectY=self.ProjectY.Offset(self.PlaneY,-offsety,sc.doc.ModelAbsoluteTolerance,Rhino.Geometry.CurveOffsetCornerStyle.Smooth)
            else:
                offsetcurve.SurfaceY=self.SurfaceY
                offsetcurve.ProjectY=[self.ProjectY]
            
            #sc.doc.Objects.AddSurface(offsetcurve.SurfaceY)
            #sc.doc.Objects.AddSurface(offsetcurve.SurfaceX)

            intcrvs=Rhino.Geometry.Intersect.Intersection.SurfaceSurface(offsetcurve.SurfaceX,offsetcurve.SurfaceY,sc.doc.ModelAbsoluteTolerance)
            offsetcurve.Base=intcrvs[1][0]
            
            #sc.doc.Objects.AddCurve(offsetcurve.Base)

            if rebuild:
                dom=offsetcurve.Base.Domain
                t=dom[0]
                l=offsetcurve.Base.GetLength(Rhino.Geometry.Interval(dom[0],dom[1]))
                cn=int(l/spacing)
                if cn<1:
                    cn=1
                step=l/cn
                ptn=[]
                for i in range(0,cn+1):
                    res,para=offsetcurve.Base.LengthParameter(t)
                    ptn.append(offsetcurve.Base.PointAt(t))
                    t+=step
                offsetcurve.Base=Rhino.Geometry.NurbsCurve.CreateControlPointCurve(ptn)
                if revpoint!=None:
                    if revpoint.DistanceTo(offsetcurve.Base.PointAtStart)>revpoint.DistanceTo(offsetcurve.Base.PointAtEnd):
                        offsetcurve.Base.Reverse()
                
            #rebuild section:
                
            
            if revpoint!=None:
                if revpoint.DistanceTo(offsetcurve.Base.PointAtStart)>revpoint.DistanceTo(offsetcurve.Base.PointAtEnd):
                    offsetcurve.Base.Reverse()
            
            return offsetcurve
        
        def TranslateNormal(self,offsetx=None,offsety=None,revpoint=None,rebuild=True,spacing=50):
            
            #loggin.info("@ProfileAxis.ProfileCurve.Offset()")

            offsetcurve=ProfileAxis().ApproxCrvs[0]
            
            #NOTE::
            #übergebene Normalenrichtung wird nicht geändert und bleibt beim offset erhalten
            if offsetx!=None:
                offsetcurve.SurfaceX=self.SurfaceX.Offset(offsetx,sc.doc.ModelAbsoluteTolerance)
            else:
                offsetcurve.SurfaceX=self.SurfaceX
            
            if offsety!=None:
                offsetcurve.SurfaceY=self.SurfaceY.Offset(offsety,sc.doc.ModelAbsoluteTolerance)
            else:
                offsetcurve.SurfaceY=self.SurfaceY
            
            # sc.doc.Objects.AddSurface(offsetcurve.SurfaceY)
            # sc.doc.Objects.AddSurface(offsetcurve.SurfaceX)

            intcrvs=Rhino.Geometry.Intersect.Intersection.SurfaceSurface(offsetcurve.SurfaceX,offsetcurve.SurfaceY,sc.doc.ModelAbsoluteTolerance)
            offsetcurve.Base=intcrvs[1][0]
            
            # sc.doc.Objects.AddCurve(offsetcurve.Base)

            if rebuild:
                dom=offsetcurve.Base.Domain
                t=dom[0]
                l=offsetcurve.Base.GetLength(Rhino.Geometry.Interval(dom[0],dom[1]))
                cn=int(l/spacing)
                if cn<1:
                    cn=1
                step=l/cn
                ptn=[]
                for i in range(0,cn+1):
                    res,para=offsetcurve.Base.LengthParameter(t)
                    ptn.append(offsetcurve.Base.PointAt(t))
                    t+=step
                offsetcurve.Base=Rhino.Geometry.NurbsCurve.CreateControlPointCurve(ptn)
                if revpoint!=None:
                    if revpoint.DistanceTo(offsetcurve.Base.PointAtStart)>revpoint.DistanceTo(offsetcurve.Base.PointAtEnd):
                        offsetcurve.Base.Reverse()
                
            #rebuild section:
                
            
            if revpoint!=None:
                if revpoint.DistanceTo(offsetcurve.Base.PointAtStart)>revpoint.DistanceTo(offsetcurve.Base.PointAtEnd):
                    offsetcurve.Base.Reverse()
            
            return offsetcurve

        def Show(self,suffix="",crv=False,srf=False,name=""):

            #loggin.info("@ProfileAxis.ProfileCurve.Show()")
            dic={"base":self.Base,"projectxy":(self.ProjectX,self.ProjectY),"srfxy":(self.SurfaceX,self.SurfaceY)}

            if srf:
                for dirxy,srfxy in zip(("X","Y"),(self.SurfaceX,self.SurfaceY)):
                    if srfxy!=None:
                        la="approx-srf-"+dirxy+suffix
                        rs.AddLayer(la)
                        s=sc.doc.Objects.AddSurface(srfxy)
                        rs.ObjectName(s,name+"_S"+dirxy)
                        rs.ObjectLayer(s,la)

            if crv:
                for dirxy,crvxy in zip(("X","Y"),(self.ProjectX,self.ProjectY)):
                    if crvxy!=None:
                        la="approx-crv-"+ dirxy +suffix
                        rs.AddLayer(la)
                        for crvxy_ in crvxy:
                            curve=sc.doc.Objects.AddCurve(crvxy_)
                            rs.ObjectName(curve,name+"_C"+dirxy)
                            rs.ObjectLayer(curve,la)

            if self.Base!=None:
                layerc="approx-curve"+suffix
                rs.AddLayer(layerc)
                curve=sc.doc.Objects.AddCurve(self.Base)
                rs.ObjectName(curve,name)
                rs.ObjectLayer(curve,layerc)

            return dic
            
            
        
###hier rework noetig ---> Geo Handling extra Klasse ###    
class CurvedProfile(Part):
    
    def __init__(self,attrib,feature,profileaxis=None,context=None,dic=None):
        
        #loggin.info("@CurvedProfile.__init__()")   
        
        self.Context=context
        self.Error=""
        self.Attrib=attrib  
        self.Axis=profileaxis
        self.Features=[feature]
        if dic==None:
            dic={}
        self.Dictionary=dic
        
    def CreateFromSweep(self,crv,srf,qsext,qsint,optimize=0,controlpointcount=20):
        
        #loggin.info("@CurvedProfile.CreateFromSweep()")  

        exthelp=500
        extsweep=5
        
        stepsize=round(rs.CurveLength(crv)/controlpointcount,1)
        gcrv=rs.coercecurve(crv)
        
        axis=ProfileAxis(basecrv=None,reference=crv,refsrf=srf,optimize=optimize,stsize=stepsize,revpoint=gcrv.PointAtStart,tolerance=3,vmean=None,offset=0)
        axis.ApproxCrvs.append(axis.ApproxCrvs[0].Offset(offsety=100,revpoint=axis.RevPoint))
        ext=axis.ApproxCrvs[1].Extend(exthelp)
        res,ts=ext.Base.ClosestPoint(axis.ApproxCrvs[0].Base.PointAtStart)
        res,te=ext.Base.ClosestPoint(axis.ApproxCrvs[0].Base.PointAtEnd)
        split=ext.Base.Split([ts,te])
        axis.ApproxCrvs[1].Base=split[1]
        #sc.doc.Objects.AddCurve(axis.ApproxCrvs[0].Base)
        #sc.doc.Objects.AddCurve(axis.ApproxCrvs[1].Base)
        #sc.doc.Objects.AddCurve(ext.Base)
        
        helpaxis=ProfileAxis()
        helpaxis.ApproxCrvs[0]=axis.ApproxCrvs[0].Extend(extsweep)
        helpaxis.ApproxCrvs.append(ext)
        res,ts=ext.Base.ClosestPoint(helpaxis.ApproxCrvs[0].Base.PointAtStart)
        res,te=ext.Base.ClosestPoint(helpaxis.ApproxCrvs[0].Base.PointAtEnd)
        split=ext.Base.Split([ts,te])
        helpaxis.ApproxCrvs[1].Base=split[1]
        #sc.doc.Objects.AddCurve(helpaxis.ApproxCrvs[0].Base)
        #sc.doc.Objects.AddCurve(helpaxis.ApproxCrvs[1].Base)
        
        extfeat=Feature(nctype=NCTypes().QSExt,brep=rs.coercecurve(qsext),layer=rs.CurrentLayer())
        intfeat=[Feature(nctype=NCTypes().QSInt,brep=rs.coercecurve(x),layer=rs.CurrentLayer()) for x in qsint]
        frame=axis.FrameAt(axis.ApproxCrvs[0].Base.PointAtStart)
        
        extfeat.Orient(frame)
        #sc.doc.Objects.AddCurve(extfeat.Brep)
        
        frame=helpaxis.FrameAt(helpaxis.ApproxCrvs[0].Base.PointAtStart)
        #rs.AddPlaneSurface(frame,500,100)
        for _,feat in enumerate(intfeat):
            feat.Orient(frame)
            #sc.doc.Objects.AddCurve(feat.Brep)
            
        sweepext=Rhino.Geometry.Brep.CreateFromSweep(axis.ApproxCrvs[0].Base,axis.ApproxCrvs[1].Base,extfeat.Brep,False,sc.doc.ModelAbsoluteTolerance)
        sweepext=sweepext[0].CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
        if sweepext.SolidOrientation==Rhino.Geometry.BrepSolidOrientation.Inward:
            sweepext.Flip()
        #sc.doc.Objects.AddBrep(sweepext)
            
        for feat in intfeat:
            sweep=Rhino.Geometry.Brep.CreateFromSweep(helpaxis.ApproxCrvs[0].Base,helpaxis.ApproxCrvs[1].Base,feat.Brep,False,sc.doc.ModelAbsoluteTolerance)
            sweepint=sweep[0].CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
            #sc.doc.Objects.AddBrep(sweepint)
            if sweepint.SolidOrientation==Rhino.Geometry.BrepSolidOrientation.Inward:
                sweepint.Flip()
            res=Rhino.Geometry.Brep.CreateBooleanDifference(sweepext,sweepint,sc.doc.ModelAbsoluteTolerance)
            sweepext=res[0]#.CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
            
        self.Axis=axis
        self.Features[0].Brep=sweepext
        self.Features.append(extfeat)
        self.Features+=intfeat
        
        return self
        
    def Copy(self,plane=None):
        
        #loggin.info("@CurvedProfile.Copy()")  

        newprofile=CurvedProfile(attrib=self.Attrib.Copy(),profileaxis=self.Axis,feature=self.Features[0].Copy(),dic=copy.deepcopy(self.Dictionary))
        for i in range(1,len(self.Features)):
            newprofile.Features.append(self.Features[i].Copy())
        
        if plane!=None:
            newprofile.Orient(plane)
        
        return newprofile   
        
    def Unroll(self,shift,offnfx,offnfy):
        
        #loggin.info("@CurvedProfile.Unroll()")  

        ext=1000
        
        #Offset NEUTRALE FASER
        nf1=self.Axis.ApproxCrvs[0].Offset(offsety=offnfy,offsetx=offnfx,revpoint=self.Axis.RevPoint)
        nf2=self.Axis.ApproxCrvs[0].Offset(offsety=offnfy,offsetx=offnfx-50,revpoint=self.Axis.RevPoint)
        crv1=nf1.Extend(ext)
        crv2=nf2.Extend(ext)
        
        ref=Rhino.Geometry.Plane.WorldXY
        ref.Origin+=ref.YAxis*shift
        #sc.doc.Objects.AddCurve(self.Axis.ApproxCrvs[0].Base)
        
        #sc.doc.Objects.AddCurve(crv1.Base)
        #sc.doc.Objects.AddCurve(crv2.Base)
        #rs.AddLine(ref.Origin,ref.Origin+ref.XAxis*crv1.Base.GetLength())
        #rs.AddLine(ref.Origin+ref.ZAxis*-50,ref.Origin+ref.ZAxis*-50+ref.XAxis*crv1.Base.GetLength())
        
        featsx=self.Features[:]
        featsx.pop(0)
        
        id=-1
        dom=crv1.Base.Domain
        
        
        channelfeats=[x for x in featsx if x.NCType==NCTypes().QSInt]
        #txt=[x for x in feats if x.NCType==NCTypes().Text]
        feats=[x for x in featsx if x.NCType!=NCTypes().QSInt]
        
        for feat in [feats,channelfeats]:
            for i,x in enumerate(feat,0):
                if x.Brep!=None:
                    if isinstance(x.Brep,Rhino.Geometry.Brep):
                        if x.Brep.IsSolid: 
                            mp=Rhino.Geometry.VolumeMassProperties.Compute(x.Brep)
                            ac=mp.Centroid
                        else:
                            mp=Rhino.Geometry.AreaMassProperties.Compute(x.Brep)
                            ac=mp.Centroid
                    else:
                        mp=Rhino.Geometry.AreaMassProperties.Compute(x.Brep)
                        ac=mp.Centroid
                    
                res,t=crv1.Base.ClosestPoint(ac)
                l=crv1.Base.GetLength(Rhino.Geometry.Interval(dom[0],t))
                vx=crv1.Base.TangentAt(t)
                res,t2=crv2.Base.ClosestPoint(crv1.Base.PointAt(t))
                vy=crv2.Base.PointAt(t2)-crv1.Base.PointAt(t)
                plane3D=Rhino.Geometry.Plane(crv1.Base.PointAt(t),vx,vy)
                plane2D=Rhino.Geometry.Plane(ref.Origin+ref.XAxis*l,ref.Origin+ref.XAxis*(l+100),ref.Origin+ref.XAxis*l+ref.ZAxis*-50)
                x.Orient(plane2D,plane3D)
                
                #rs.AddPlaneSurface(plane3D,200,100)
                #rs.AddPlaneSurface(plane2D,200,100)
                
                #if isinstance(x.Brep,Rhino.Geometry.Brep):
                #    rs.ObjectName(sc.doc.Objects.AddBrep(x.Brep),str(i))
                    
                #sc.doc.Objects.AddPoint(crv1.Base.PointAt(t))
                #rs.AddPlaneSurface(x.Plane,50,50)
                #rs.AddPoint(ref.Origin+ref.XAxis*l)
        
        lc1=Rhino.Geometry.LineCurve(Rhino.Geometry.Line(ref.Origin,ref.Origin+ref.XAxis*crv1.Base.GetLength()))
        lc2=Rhino.Geometry.LineCurve(Rhino.Geometry.Line(ref.Origin+ref.ZAxis*-50,ref.Origin+ref.ZAxis*-50+ref.XAxis*crv1.Base.GetLength()))
        brep=Rhino.Geometry.Brep.CreateFromSweep(lc1,lc2,feats[0].Brep,True,sc.doc.ModelAbsoluteTolerance)
        brep[0]=brep[0].CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
        
        for i,feat in enumerate(channelfeats):
            help=Rhino.Geometry.Brep.CreateFromSweep(lc1,lc2,feat.Brep,True,sc.doc.ModelAbsoluteTolerance)
            help[0]=help[0].CapPlanarHoles(sc.doc.ModelAbsoluteTolerance)
            br=sc.doc.Objects.AddBrep(help[0])
            channelfeats[i].Brep=rs.coercebrep(br)
            channelfeats[i].NCType=NCTypes().Freemill
            rs.DeleteObject(br)
        
        featx=self.Features[0].Copy()
        featx.Brep=brep[0]
        featx.Plane=ref
        profile=Profile(attrib=self.Attrib.Copy(),feature=featx)
        saws=[x for x in feats if x.NCType==NCTypes().Saw]
        if len(saws)==0:
            saws.append(Feature(nctype=NCTypes().Saw,name="start",plane=Rhino.Geometry.Plane(ref.Origin+ref.XAxis*ext,ref.XAxis*-1)))
            saws.append(Feature(nctype=NCTypes().Saw,name="end",plane=Rhino.Geometry.Plane(ref.Origin+ref.XAxis*(-ext+crv1.Base.GetLength(Rhino.Geometry.Interval(dom[0],dom[1]))),ref.XAxis)))
            
        otherfeats=[x for x in feats if x.NCType!=NCTypes().Saw]
        profile.ApplyFeatures(features=saws,tolerance=sc.doc.ModelAbsoluteTolerance)
        profile.ApplyFeatures(features=channelfeats,tolerance=sc.doc.ModelAbsoluteTolerance)
        profile.ApplyFeatures(features=otherfeats,tolerance=sc.doc.ModelAbsoluteTolerance)
        
        return profile
        
    def ToDic(self,savebreps=False,context=None):

        #loggin.info("@CurvedProfile.ToDic()")  

        self.UpdateObjectProperties()
        return {"TYP":"CurvedProfile","Features":[x.ToDic(savebreps,context) for x in self.Features],"Attrib":self.Attrib.ToDic(),"Dic":self.Dictionary}
                    
            
class examples:
    
    def LanglochFeature():
        
        ll=Feature(nctype=NCTypes().EHole,plane=None,sizex=10,sizey=20,sizez=-10,layer=rs.CurrentLayer())
        #ll.EnjoyJSON()
        ll.Show(sc)
        llcopy=ll.Copy(plane=rs.PlaneFromNormal([1,20,33],[0,45,7]))
        llcopy.Show(sc)
        
    def RechteckFeature():
        
        rt=Feature(nctype=NCTypes().RHole,plane=rs.PlaneFromNormal([14,-33,-50],[10,33,77]),sizex=50,sizey=30,sizez=-20,radius=5)
        rt.ShowBrep()
        rt.Orient(plane=Rhino.Geometry.Plane.WorldXY)
        rt.ShowBrep()
        
    def TextFeature():
        
        plane =rs.PlaneFromNormal([44,-150,-50],[10,33,300])
        plane.Flip()
        brep=Rhino.Geometry.Box(plane,Rhino.Geometry.Interval(-100,300),Rhino.Geometry.Interval(-100,100),Rhino.Geometry.Interval(-10,0)).ToBrep()
        part=Part(attrib=Attrib(),feature=Feature(brep=brep,layer=rs.CurrentLayer()))
        txt=Feature(name='Test',text="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+-",nctype=NCTypes().Text,plane=plane,sizez=2.,sizey=8.)
        part.ApplyFeatures(sc.doc.ModelAbsoluteTolerance,txt)
        part.Show(sc)
    
    class JSON:
        
        def ToJSON():
        
            bo=Part(Attrib(rawmat="alustab"),Feature(unrolz=41,ro=2700,objectid=None))
            bo.Features.append(Feature(name='Test',text="B4403-0001",nctype=NCTypes().Text,plane=rs.PlaneFromNormal([44,-33,-50],[10,33,77]),sizey=20,sizez=-0.5))
            print(bo)
            with open("C:\Users\JTEST.json",'w') as file:
                file.write(bo.ToJSON(savebreps=False))
                file.close()
            
        def FromJSON():
            with open("C:\Users\JTEST.json",'r') as file:
                string=file.read()
                file.close()
            bo=Part().FromJSON(string)
            print(bo)
            
        def LookAtIt():
            bo=Part(Attrib(rawmat="alustab"),Feature(unrolz=41,ro=2700,objectid=None))
            bo.EnjoyJSON()
       
        def AttribToJSON(self):
            
            path=PATH_ATTRIB_MAP
            res=Archive().FromJSON(PATH_ATTRIB_MAP)
            a=Archive()
            
            keymap={"ZusatzText":"Description","APVorlage":"CostCentre","Einkauf":"Purchase","Lager":"Production","Auftrag":"Order","Lager":"Storage","VBME":"Units","Menge":"Count"}
            for key in keymap:
                a.__dict__[key]=keymap[key]
            
            
            file.write(Feature().ToJSON())
        
        
    def Part():
        at=Attrib(id="0001",prefix="B4010",zusatztext="Canopy Profile 0°/2°",rawmat="1745-WN3083820-5700",fincode="03",matcode="321",apvorlageno="V-AL09",einkauf="",fertigung="X",auftrag="X",lager="",vbme="Stück",textpos=False)
        ft=Feature(name="2",objectid=rs.GetObject(),create=True,file="WN3083820_b_2.3dm",ro=2700,nccreate=True)
        print(Part(at,ft).ToAPArtikel())
        
        return None
        
    def Profile():
        
        #at=Attrib(id="the_ONE",prefix="B4010",zusatztext="Canopy Profile",rawmat="1745-WN3083820-5700",fincode="03",matcode="321",apvorlageno="V-AL09",einkauf="",fertigung="X",auftrag="X",lager="",vbme="Stück",textpos=False)
        #ft=Feature(name="2",create=True,file=r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\1745_qs\WN3083820_b_2.3dm",ro=2700,nccreate=True,layer=rs.CurrentLayer())

        at=Attrib(id="the_ONE",prefix="B4010",zusatztext="Canopy Profile",rawmat="1745-WN3083820-5700",fincode="03",matcode="321",apvorlageno="V-AL09",einkauf="",fertigung="X",auftrag="X",lager="",vbme="m",textpos=False)
        ft=Feature(name="2",sizey=100,sizez=100,sizex=2000,create=False,ro=2700,nccreate=True,layer=rs.CurrentLayer())
        
        prof=Profile(at,ft)
        
        prod=Product(feature=Feature(),attrib=Attrib())
        prod.Profiles.append(prof)
        
        #prof.Show(sc)
        #prof.Copy(rs.PlaneFromNormal([1,20,33],[0,45,7])).Show(sc)
        print prod.ToAPArtikel()
        
        return  
        
        
        at=Attrib(id="the_ONE",prefix="B4010",zusatztext="Canopy Profile",rawmat="1745-WN3083820-5700",fincode="03",matcode="321",apvorlageno="V-AL09",einkauf="",fertigung="X",auftrag="X",lager="",vbme="Stück",textpos=False)
        ft=Feature(name="2",brep=rs.coercebrep(rs.GetObject("pick profil",rs.filter.polysurface)),create=True,file="WN3083820_b_2.3dm",ro=2700,nccreate=True)
        prof=Profile(at,ft)
        prof.Features.append(Feature(name="hole",brep=rs.coercebrep(rs.GetObject("pick feature",rs.filter.polysurface)),nccreate=False))
        prof.Features.append(Feature(name="saw",plane=rs.PlaneFromPoints(rs.GetPoint("pick saw origin"),rs.GetPoint("pick saw point in x direction"),rs.GetPoint("pick saw point in y direction")),nccreate=False,nctype=NCTypes().Saw))
        print(prof.ToAPArtikel())
        
        prof2=prof.Copy(plane=rs.PlaneFromPoints(rs.GetPoint("pick orient origin"),rs.GetPoint("pick orient point in x direction"),rs.GetPoint("pick orient point in y direction")))
        prof2.Attrib.ID="the_COPIED_ONE"
        prof2.ApplyFeatures()
        prof2.ShowPart()
        print(prof2.ToAPArtikel())
        
        #prof2.EnjoyJSON()
        
        return None
        
    def Product():
        
        x=True
        if not x:
            #Rebuild FromJSON
            f=open(r"C:\Users\lippert_sebastian.SEELE\Desktop\NeuerOrdner\temp.json",'r')
            prod=Product()
            prod.FromJSON(f.read())
            prod.Show()
            print prod
            return
         
        if x:
            #ToJSON
            axis=rs.coercegeometry(rs.GetObject())
            at=Attrib(id="profile",prefix="B4010",zusatztext="Canopy Profile",rawmat="1745-WN3083820-5700",fincode="03",matcode="321",apvorlageno="V-AL09",einkauf="",fertigung="X",auftrag="X",lager="",vbme="m",textpos=False)
            ft=Feature(name="B",create=True,axis=axis,file=r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\1745_qs\WN3083820_b_2.3dm",ro=2700,nccreate=True)
            prof=Profile(at,ft)
            
            at=Attrib(id="product",prefix="B4000",zusatztext="Canopy Profile ASM",rawmat="",fincode="01",matcode="00",apvorlageno="V-AL21",einkauf="",fertigung="X",auftrag="X",lager="")
            ft=Feature(name="A",plane=None)
            prod=Product(at,ft)
            prod.Profiles.append(prof)
            
            #print prod.ToAPArtikel()
            SaveAsciFile(prod.ToJSON(),r"C:\Users\lippert_sebastian.SEELE\Desktop\NeuerOrdner\temp.json")   
            prod.Show()
        
        return True
        
    def Sheet():
        
        #sheet test durchführen...
        at=Attrib(id="0001",prefix="B4050",zusatztext="Test-Sheet",rawmat="1000020008",fincode="03",matcode="321",apvorlageno="V-AL09",einkauf="",fertigung="X",auftrag="X",lager="",vbme="m2",textpos=False)
        ft=Feature(name="KEF",create=True,ro=2700,nccreate=True,plane=rs.TextObjectPlane(rs.GetObject("pick text",rs.filter.annotation)))
        sheet=Sheet(attrib=at,feature=ft)
        sheet.Brep(rs.GetObject("pick brep",rs.filter.polysurface))
        dwg=sheet.ToDrawing()
        if dwg==None:
            print sheet.Error
        print sheet.ToAPArtikel()
        
        return dwg
        
    def APFromJSON():
        
        with open(r"C:\Users\lippert_sebastian.SEELE\Desktop\test.json",'r') as file:
            string=file.read()
            file.close()
        xx=SaveAsciFile(str(APArtikel().FromJSON(string)),r"C:\Users\lippert_sebastian.SEELE\Desktop\PYthonic\test.txt")
        
        return 
        
    def CurvedProfile():
        
        #Generierung der ExampleGeometrie
        #######################################################################################
        #######################################################################################
        
        sizex=1000
        sizez=10
        vec=Rhino.Geometry.Plane.WorldXY.XAxis*sizex
        pt=[]
        
        circle=Rhino.Geometry.Circle(1000)
        rsrf=Rhino.Geometry.Cylinder(circle,3600).ToBrep(False,False)
        
        feats=[]
        for i in range(0,360,10):
            vec2=rs.VectorRotate(vec,i,Rhino.Geometry.Plane.WorldXY.ZAxis)
            p=Rhino.Geometry.Plane.WorldXY.Origin+vec2+Rhino.Geometry.Plane.WorldXY.ZAxis*i*sizez
            pt.append(p)
            feat=Feature(nctype=NCTypes().Hole,sizex=150,sizez=100,plane=rs.PlaneFromNormal(p,vec2),layer=rs.CurrentLayer())
            feats.append(feat)
            #feat.Show(sc)
            
        rcrv=rs.AddInterpCurve(pt)
        axis=rs.coercecurve(rcrv)
        
        #QS auf PlaneXY erstellen
        pl=Rhino.Geometry.Plane.WorldXY 
        pl.Origin+=pl.XAxis*-50+pl.YAxis*-100
        crext=rs.AddRectangle(pl,100,200)
        pl.Origin+=pl.XAxis*50+pl.YAxis*100
        pl.Origin+=pl.XAxis*-40+pl.YAxis*-90
        crint=[rs.AddRectangle(pl,30,150)]
        pl.Origin+=pl.XAxis*40+pl.YAxis*90
        crint.append(rs.AddRectangle(pl,40,90))
        
        #######################################################################################
        #######################################################################################
        
        #rcrv=rs.GetObject()
        #rsrf=rs.GetObject()
        #crext=rs.GetObject()
        #crint=[]
        
        cp=CurvedProfile(Attrib(id="uschi-100"),Feature(layer=rs.CurrentLayer())).CreateFromSweep(rcrv,rsrf,crext,crint)
        #cp.ApplyFeatures(sc.doc.ModelAbsoluteTolerance,feats)
        cp.Show(sc,writeattribtoobject=True)
        
        cpunrol=cp.Unroll(0,0,0)
        cpunrol.Show(sc,writeattribtoobject=True)
        
        rs.DeleteObject(rcrv)
        rs.DeleteObject(crext)
        rs.DeleteObjects(crint)
        
        return None


if __name__=="__main__":
    #examples().LanglochFeature()
    #examples().Profile()
    #examples().Sheet()
    #examples().TextFeature()
    examples().JSON().AttribToJSON()
    
else:
    print "invoking from baseobjects.py"
    #print(sys.path[0]+r"\baseobjects_debug.log")
    #loggin.info("@invoking baseobjects_WIP")
