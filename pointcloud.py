# -*- encoding: utf-8 -*-
"""
Script written by S. Lippert for Seele GmbH
Version 1.0 as of XXXX-XX-XX
Version 2.0 as of 2018-05-03
Version 3.0 as of 2019-10-21
Copyright by Seele GmbH
"""

import sys
import System.Drawing.Color as Color
import random 
import System.Guid
import time

import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc

sys.path.append(r"G:\DAT\TECHARCH\TB-Entwicklungen\Rhino_Programmierung\seele.Rhino.Common")
import visualize as viz


class Cloud(object):

    def __init__(self,cldguid=None,cld=None,ptguids=None,ptcoos=None):
        
        if cldguid!=None:
            self.CLD=rs.coercegeometry(cldguid)
        elif cld!=None:
            self.CLD=cld
        elif ptguids!=None:
            self.CLD=Rhino.Geometry.PointCloud([rs.PointCoordinates(x)for x in ptguids])
        elif ptcoos!=None:
            self.CLD=Rhino.Geometry.PointCloud(ptcoos)
        else:
            self.CLD=Rhino.Geometry.PointCloud()
        
        #self.Tree=Rhino.Geometry.RTree.CreatePointCloudTree(self.CLD)
    
    def Count(self):
        return self.CLD.Count

    def Join(self,cldguid=None):
        if cldguid!=None:
            if not isinstance(cldguid,list):
                cldguid=[cldguid]
            for c in cldguid:
                pc=rs.coercegeometry(c)
                cols=pc.GetColors()
                pts=pc.GetPoints()
                if len(pts)==len(cols):
                    self.CLD.AddRange(pts,cols)
                else:
                    self.CLD.AddRange(pts)
        return True
    
    def ApplyColors(self,colors):
        cn=0
        for pcitem in self.CLD:
            pcitem.Color=rs.coercecolor(colors[cn])
            cn+=1
        
    #solves the potential risk of a gigantic & very sparse list
    def Reduce(self,factor=None,threshold=None,red_cell_ac=False,red_cell_ac_clo=False,red_mean=False,red_all=False,mindensity=1):
        """calcs a pointcloud with reduced point count - if threshold option is used point will be colorized with heatvalues shwoing point density in neighbourhood
        Parameters:
          factor (float, optional):         if set, cloud will be reduced by factor ex. 0.01==every 100th element will be used for new cloud
          threshold (float, optional):      if set, cloud will be reduced to match def. cell size
          red_cell_ac (bool, optional):     if True, points in cell will be replaced by cell areacentroid
          red_cell_ac_clo (bool, optional): if True, points in cell will be replaced by cell areacentroid closestpoint 
          red_mean (bool, optional):        if True, points in cell will be replaced by mean 
          red_all (bool, optional):         if True, points in cell will not be replaced  
          mindensity (int, optional):       if True, only cells with points>mindensitsy are used for new cloud
        Returns:
          Cloud: self
        Example:
            use red_all + mindensity for noise reduction!!!
            cld=Cloud(cldguid=rs.GetObject("pick point-cloud"))
            cld.Reduce(threshold=10,mindensity=10).Show("th=10--md=10")
        See Also:
        """
        
        t1=time.time()
        
        if factor!=None:
            pcn=Rhino.Geometry.PointCloud()
            pcl=self.CLD.GetPoints()
            col=self.CLD.GetColors()
            ids=range(len(pcl))
            random.shuffle(ids)
            pcl=[pcl[i] for i in ids]
            if len(col)==len(ids):
                col=[col[i] for i in ids]
                for i in range(0,len(pcl),int(1./float(factor))):
                    pcn.Add(pcl[i],col[i])
            else:
                pcn.AddRange([pcl[i] for i in range(0,len(pcl),int(1/factor))])
            self.CLD=pcn
            
            self._Time(t1,time.time())
            
        elif threshold!=None:  
            
            maxheat=int(threshold/0.5)#assumption scandaten sind nicht dichter als 0.5mm
            
            ptcoo,colors,dic,bbx=self.__Slice(threshold,threshold,threshold)
            self.CLD=Rhino.Geometry.PointCloud()
            
            cn=0
            cn1=0
            for key in dic:
                if len(dic[key][1])>mindensity:
                    keys=dic[key][1]
                    ix=dic[key][0][0]
                    iy=dic[key][0][1]
                    iz=dic[key][0][2]
                    
                    pts=[ptcoo[i] for i in keys]
                    
                    if red_all:
                        ac=pts
                    elif red_cell_ac:
                        ac=[
                        bbx.Min+
                        Rhino.Geometry.Plane.WorldXY.XAxis*(ix+0.5)*threshold+
                        Rhino.Geometry.Plane.WorldXY.YAxis*(iy+0.5)*threshold+
                        Rhino.Geometry.Plane.WorldXY.ZAxis*(iz+0.5)*threshold
                        ]
                    elif red_cell_ac_clo:
                        ac=bbx.Min+Rhino.Geometry.Plane.WorldXY.XAxis*(ix+0.5)*threshold+Rhino.Geometry.Plane.WorldXY.YAxis*(iy+0.5)*threshold+Rhino.Geometry.Plane.WorldXY.ZAxis*(iz+0.5)*threshold
                        id=rs.PointArrayClosestPoint(pts,ac)
                        ac=[pts[id]]
                    elif red_mean:
                        ac=[reduce(lambda x,y:x+y,pts)/len(pts)]
                    
                    for p in ac:
                        heatcol=viz.CalcColorValues(range(maxheat),val=len(pts))
                        self.CLD.Add(p,rs.coercecolor(heatcol))
                        
                if cn>int(len(dic)/10): 
                    self._Time(t1,time.time(),"{0:.1f}%".format((cn1/len(dic))*100))
                    cn=0
                cn+=1
                cn1+=1
                
        return self
    
    def __Slice(self,sizex=1000,sizey=1000,sizez=1000):
        
        bbx=self.CLD.GetBoundingBox(False)
        
        dic={}
            
        ptcoo=self.CLD.GetPoints()
        ptcol=self.CLD.GetColors()
        
        for i,p in enumerate(ptcoo):
            idx=int((p.X-bbx.Min.X)/sizex)
            idy=int((p.Y-bbx.Min.Y)/sizey)
            idz=int((p.Z-bbx.Min.Z)/sizez)
            key="{0:d}x{1:d}x{2:d}".format(idx,idy,idz)
            #rs.AddPoint(bbx.Min+Rhino.Geometry.Plane.WorldXY.XAxis*idx*sizex+Rhino.Geometry.Plane.WorldXY.YAxis*idy*sizey+Rhino.Geometry.Plane.WorldXY.ZAxis*idz*sizez)
            if key in dic:
                dic[key][1].append(i)
            else:
                dic[key]=[(idx,idy,idz),[i]]
        
        return ptcoo,ptcol,dic,bbx
        
    def Split(self,sizex=1000,sizey=1000,sizez=1000,layer="split-cloud"):
        
        t1=time.time()
        
        ptcoo,ptcol,dic,bbx=self.__Slice(sizex,sizey,sizez)
        clds=[]
        rs.AddLayer(layer)
        for key in dic:
            if len(dic[key][1])>0:
                keys=dic[key][1]
                i=dic[key][0][0]
                j=dic[key][0][1]
                k=dic[key][0][2]
                
                cld=Rhino.Gemetry.PointCloud()
                try:
                    _=[cld.Add(ptcoo[i],ptcol[i]) for i in keys]
                except:
                    cld.AddRange([ptcoo[i] for i in keys])
                clds.append(Cloud(cld=cld))
                clds[-1].Show(layer)
        
        self._Time(t1,time.time())
        
        return clds
    
    def _Time(self,t1,t2,string=""):
        print "duration: {0:.2f} min.--->{1:s}".format((t2-t1)/60,string)
    
    def Show(self,layer="newcloud",plane=None):
        if plane!=None:
            pcl=self.CLD.GetPoints()
            col=self.CLD.GetColors()
            
            self.CLD=self.CLD=Rhino.Geometry.PointCloud()
            for i,p in enumerate(pcl):
                coo=rs.XformCPlaneToWorld(p,plane)
                self.CLD.Add(coo,col[i])
        
        if self.CLD.Count>0:
            cldobj=sc.doc.Objects.AddPointCloud(self.CLD)
            rs.AddLayer(layer)
            rs.ObjectLayer(cldobj,layer)
        
    def GetPointsClosestClouds(self,points,thresh,split=True):
        
        if not isinstance(points,list):
            points=[points]
        if isinstance(points[0],System.Guid):
            points=[rs.PointCoordinates(x) for x in points]
        if not isinstance(points[0],Rhino.Geometry.Point3d):
            print "unable to convert input data"
            return
        
        newcldpts=[[] for x in points]
        
        #pcl=self.CLD.GetPoints()
        time1=time.time()
        cn=100000
        for i in range(0,self.CLD.Count):
            cloud_point=self.CLD.Item[i].Location
            
            if i%cn==0:
                cn+=100000
                time2=time.time()
                print str(int(i/self.CLD.Count*100))+"% time elapsed " + str(round((time2-time1)/60 ,2)) 
                rs.Redraw()
            
            id=rs.PointArrayClosestPoint(points,cloud_point)
            if cloud_point.DistanceTo(points[id])<thresh:
                newcldpts[id].append(cloud_point)
        
        if split:
            nclds=[]
            for i,points in enumerate(newcldpts):
                nclds.append(Cloud(Rhino.Geometry.PointCloud(points)))
            return nclds
            
        else:
            ncld=Cloud()
            for i,points in enumerate(newcldpts):
                Cloud.CLD.AddRange(points)
            return ncld

    def GetPlaneClosestCloud(self,plane,threshold,split=True,project=True):
        
        newcldpts=[]
        
        time1=time.time()
        cn=100000
        for i in range(0,self.CLD.Count):
            cloud_point=self.CLD.Item[i].Location
            
            if i%cn==0:
                cn+=100000
                time2=time.time()
                #print i
                #print self.CLD.Count
                print str(int(float(i)/float(self.CLD.Count)*100))+"% time elapsed " + str(round((time2-time1)/60 ,2)) 
                rs.Redraw()
            
            proj=plane.ClosestPoint(cloud_point)
            if cloud_point.DistanceTo(proj)<threshold:
                if project:
                       newcldpts.append(proj)
                else:      
                   newcldpts.append(cloud_point)
    
        ncld=Cloud()
        ncld.CLD.AddRange(newcldpts)
                
        return ncld

    def GetPtNeighbours(self,point,thresh):
        
        if not isinstance(point,Rhino.Geometry.Point3d):
            return
        
        return self.Tree.Search(Rhino.Geometry.Sphere(point,thresh))
    
    def GetMeshClosestPoints_(self,mesh,thresh=None):
        
        if mesh==None:
            return
        if isinstance(mesh,System.Guid):
            if rs.IsMesh(mesh):
                mesh=rs.coercemesh(mesh)
            else:
                return
            
        pcl=self.CLD.GetPoints()
        col=self.CLD.GetColors()
        pcn=Rhino.Geometry.PointCloud()
        
        time1=time.time()
        cn=100000
        for i,p in enumerate(pcl):
            if i%cn==0:
                cn+=100000
                time2=time.time()
                print str(int(i/self.CLD.Count*100))+"% time elapsed " + str(round((time2-time1)/60 ,2)) 
                rs.Redraw()
            
            cp=mesh.ClosestPoint(p)
            if thresh==None:
                #if i<len(col):
                pcn.Add(p)#,col[i])
            else:
                if p.DistanceTo(cp)<thresh:
                    pcn.Add(p)#,col[i])
                    
        return Cloud(cld=pcn)
        
    def GetMeshClosestPoints(self,mesh,thresh=None):
        
        if mesh==None:
            return
        if isinstance(mesh,System.Guid):
            if rs.IsMesh(mesh):
                mesh=rs.coercemesh(mesh)
            else:
                return
            
        pcn=Rhino.Geometry.PointCloud()
        
        time1=time.time()
        cn=100000
        i=0
        ds=[]
        for pcitem in self.CLD:
            if i%cn==0:
                cn+=100000
                time2=time.time()
                print str(int(i/self.CLD.Count*100))+"% time elapsed " + str(round((time2-time1)/60 ,2)) 
                rs.Redraw()
            
            cp=mesh.ClosestPoint(pcitem.Location)
            ds.append(pcitem.Location.DistanceTo(cp))
            
            if thresh==None:
                pcn.Add(pcitem.Location,pcitem.Color)
            else:
                if ds[-1]<thresh:
                    pcn.Add(pcitem.Location,pcitem.Color)
            i+=1         
            
        return Cloud(cld=pcn),ds
    
    def GetMeshClosestPointsQuartile(self,mesh,thresh=None,threshlow=0.25,treshhigh=0.75):
        
        if mesh==None:
            return
        if isinstance(mesh,System.Guid):
            if rs.IsMesh(mesh):
                mesh=rs.coercemesh(mesh)
            else:
                return
            
        pcl=self.CLD.GetPoints()
        col=self.CLD.GetColors()
        pcn=Rhino.Geometry.PointCloud()
        
        try:
            time1=time.time()
            cn=100000
            pcollect=[]
            devcollect=[]
            for i,p in enumerate(pcl):
                if i%cn==0:
                    cn+=100000
                    time2=time.time()
                    print str(int(i/self.CLD.Count*100))+"% time elapsed " + str(round((time2-time1)/60 ,2)) 
                    rs.Redraw()
                
                cp=mesh.ClosestPoint(p)
                testvec=p-cp
                alpha=rs.VectorAngle(testvec,Rhino.Geometry.Vector3d.ZAxis)
                if alpha<45 or alpha>135:
                    continue
                else:
                    if thresh==None:
                        pcn.Add(p)
                    else:
                        dev=p.DistanceTo(cp)
                        if dev<thresh:
                            devcollect.append(dev)
                            pcollect.append((dev,p))

                    
            ma,mi=max(devcollect),min(devcollect)
            idlow=int(len(devcollect)*threshlow)
            idhigh=int(len(devcollect)*treshhigh)
            pcollectsort=sorted(pcollect,key=lambda x:x[0])[idlow:idhigh]
            pcn.AddRange([x[1] for x in pcollectsort])
            
            return Cloud(cld=pcn)
        except:
            return None
        
    def GetBrepClosestPoints(self,brep,thresh=None):
        
        if brep==None:
            return
        if isinstance(brep,System.Guid):
            if rs.IsBrep(brep):
                brep=rs.coercebrep(brep)
            else:
                return
            
        pcl=self.CLD.GetPoints()
        col=self.CLD.GetColors()
        pcn=Rhino.Geometry.PointCloud()
        for i,p in enumerate(pcl):
            cp=brep.ClosestPoint(p)
            if thresh==None:
                pcn.Add(p)
            else:
                if p.DistanceTo(cp)<thresh:
                    pcn.Add(p)
                    
        return Cloud(cld=pcn)
    
    def GetCurvesClosestPoints(self,crvs,thresh=None,fav=None):
        
        pcl=self.CLD.GetPoints()
        col=self.CLD.GetColors()
        pcn=Rhino.Geometry.PointCloud()
        pcnp=Rhino.Geometry.PointCloud()

        for i,p in enumerate(pcl):
            co=rs.PointClosestObject(p,crvs)
            cp=co[1]
            if fav!=None:
                if crvs.index(co[0])!=fav:
                    continue
            if thresh==None:
                    pcn.Add(p)
                    pcnp.Add(cp)
            else:
                if p.DistanceTo(cp)<thresh:
                    pcn.Add(p)
                    pcnp.Add(cp)
                
        return Cloud(cld=pcn),Cloud(cld=pcnp)
    
    def BuildDeviationVectorToMesh(self,mesh,thresh=50,scale=1):
        
        if mesh==None:
            return
        if isinstance(mesh,System.Guid):
            if rs.IsMesh(mesh):
                mesh=rs.coercemesh(mesh)
            else:
                return
            
        pcl=self.CLD.GetPoints()
        col=self.CLD.GetColors()
        pcn=Rhino.Geometry.PointCloud()
        
        time1=time.time()
        cn=100000
        vecs=[]
        for i,p in enumerate(pcl):
            if i%cn==0:
                cn+=100000
                time2=time.time()
                print str(int(i/self.CLD.Count*100))+"% time elapsed " + str(round((time2-time1)/60 ,2)) 
            
            vecs.append(p-mesh.ClosestPoint(p))
        
        try:
            ac=reduce(lambda x,y:x+y,pcl)/len(pcl)
            vec=reduce(lambda x,y:x+y,vecs)/len(vecs)
        except:
            return None
        return rs.AddLine(ac,ac+vec*scale)

    def Copy(self):
        return Cloud(cld=self.CLD.Duplicate())
    
    def FitCross(self,plane):
        
        pt=Rhino.Geometry.Point3d(0,0,0)
        pts=[]
        for j in range(0,self.CLD.Count):
            pt+=self.CLD.Item[j].Location
            pts.append(self.CLD.Item[j].Location)
        pt/=self.CLD.Count
        plane_=Rhino.Geometry.Plane(plane)
        plane_.Origin=pt
        
        
        
        mean=pt
        hist=[mean]
        ptnew=pts
        while True:
            newp=[]
            for p in ptnew:
                if p.DistanceTo(mean)<50:
                    newp.append(p)
            mean=reduce(lambda x,y: x+y, newp)/len(newp)
            if hist[-1].DistanceTo(mean)<0.1:
                hist.append(mean)
                break
            hist.append(mean)
            
        pt=mean
        points=[]   
        for j in range(0,self.CLD.Count):
            v= self.CLD.Item[j].Location-pt
            if v.Length>30:
                points.append(self.CLD.Item[j].Location)
        
        
        min=1000000000000000000.
        plmin=None
        minpt=None
        maxpt=None
        
        
        for i in range(0,180):
            errs=[]
            pl=rs.RotatePlane(plane_,i/1.,plane.ZAxis)
            for j in points:
                errs.append(rs.XformWorldToCPlane(j,pl))
            sorted_=sorted(errs,key=lambda x:abs(x.X))
            sortedx,sortedy=self._SortPoints(sorted_)
            scale=reduce(lambda x,y:x+y,[abs(z.X) for z in sortedx])
            if scale<min:
                min=scale
                plmin=pl
                minpt=sortedx
                maxpt=sortedy
        
        minpt=[rs.XformCPlaneToWorld(rs.XformCPlaneToWorld(x,plmin),plane) for x in minpt]
        maxpt=[rs.XformCPlaneToWorld(rs.XformCPlaneToWorld(x,plmin),plane) for x in maxpt]
        
        rs.AddPointCloud(minpt)
        
        rs.AddPointCloud(maxpt)
        
        l1=rs.LineFitFromPoints(minpt)
        l2=rs.LineFitFromPoints(maxpt)
        l1=rs.AddLine(*l1)
        l2=rs.AddLine(*l2)
        
        return rs.LineLineIntersection(l1,l2)[0],l1,l2
    
    def FitCrossKMeans(self,plane):
        
        pt=Rhino.Geometry.Point3d(0,0,0)
        pts=[]
        for j in range(0,self.CLD.Count):
            pt+=self.CLD.Item[j].Location
            pts.append(self.CLD.Item[j].Location)
        pt/=self.CLD.Count
        plane_=Rhino.Geometry.Plane(plane)
        plane_.Origin=pt
        ac=pt
        
        
        mean=pt
        hist=[mean]
        ptnew=pts
        while True:
            newp=[]
            for p in ptnew:
                if p.DistanceTo(mean)<50:
                    newp.append(p)
            mean=reduce(lambda x,y: x+y, newp)/len(newp)
            if hist[-1].DistanceTo(mean)<0.1:
                hist.append(mean)
                break
            hist.append(mean)
            
        pt=mean
        points=[]   
        for j in range(0,self.CLD.Count):
            v= self.CLD.Item[j].Location-pt
            if v.Length>30:
                points.append(self.CLD.Item[j].Location)
        
        #minpt,maxpt=self._KMeans(points,plane,ac)
                                 
        #return 
        
        #minpt=[rs.XformCPlaneToWorld(rs.XformCPlaneToWorld(x,plmin),plane) for x in minpt]
        #maxpt=[rs.XformCPlaneToWorld(rs.XformCPlaneToWorld(x,plmin),plane) for x in maxpt]
        
        ls=[]
        l=[]
        for j,points in enumerate(self._KMeans(points,plane,ac)):
            pts=[rs.XformCPlaneToWorld(x,plane) for x in points]
            rs.AddPointCloud(pts)
            l.append(rs.LineFitFromPoints(pts))
            ls.append(rs.AddLine(*l[-1]))
        
        return rs.LineLineIntersection(l[0],l[1])[0],ls[0],ls[1]
    
    def _SortPoints(self,points):
        
        id=int(len(points)/2)
        errlow=[abs(x.X) for x in points[:id]]
        errhigh=[abs(x.X) for x in points[id:]]
        
        meanlow=reduce(lambda x,y:x+y,errlow)/len(errlow)
        meanhigh=reduce(lambda x,y:x+y,errhigh)/len(errhigh)
        
        low,high=[],[]
        for p in points:
            if abs((meanlow-abs(p.X)))<abs((meanhigh-abs(p.X))):
                low.append(p)
            else:
                high.append(p)
        return low,high
    
    def _KMeans(self,points,plane,ac,grpcount=4):
        
        
        means=[]
        vec=plane.XAxis
        step=int(360/grpcount)
        for i in range(grpcount):
            vec=rs.VectorRotate(vec,step,plane.ZAxis)
            means.append(rs.XformWorldToCPlane(plane.Origin+vec*200,plane))
        
        grps=[points]
        
        mhist=[[] for x in means]
        for j in range(10):
            if j>0:
                for l,grp in enumerate(grps):
                    if len(grp)>0:
                        means[l]=reduce(lambda x,y:x+y,grp)/len(grp)
            
            #rs.AddPoints([rs.XformCPlaneToWorld(x,plane) for x in means])
            grpsnew=[[] for x in means]
            for grp in grps:
                for point in grp:
                    min=100000000.
                    id=-1
                    for i,mean in enumerate(means):
                        d=mean.DistanceTo(point)
                        if d<min:
                            min=d
                            id=i
                    grpsnew[id].append(point)
            grps=grpsnew
            for k,m in enumerate([rs.XformCPlaneToWorld(x,plane) for x in means]):
                mhist[k].append(m)
        
        #for pts in mhist:
        #    rs.AddPolyline(pts)
        
        v1=means[0]-ac
        max=0
        id=-1
        for j in range(1,4):
            v2=means[j]-ac
            angle=rs.VectorAngle(v1,v2)
            if angle>max:
                max=angle
                id=j
        ids=[x for x in [1,2,3] if x!=id]
        
        if len(grps[0])>len(grps[id]):
            export1=grps[0]
        else:
            export1=grps[id]

        if len(grps[ids[0]])>len(grps[ids[1]]):
            export2=grps[ids[0]]
        else:
            export2=grps[ids[1]]

        
        return [export1,export2]
               

def debug():
    
    cld=Cloud(rs.GetObject("sel cloud to manipulate",rs.filter.pointcloud))
    
    #res=cld.GetMeshClosestPoints(rs.GetObject("sel mesh as ref", rs.filter.mesh),100)
    #res=cld.BuildDeviationVectorToMesh(rs.GetObject("sel mesh as ref", rs.filter.mesh),thresh=50,scale=1000)
    res=cld.GetPlaneClosestCloud(rs.GetObject("sel mesh as ref", rs.filter.surface),5,split=True,project=True)
    #join=cld.Join(cldguid=rs.GetObjects("",rs.filter.pointcloud))
    res.Show()
    
    #cld.Join(rs.GetObject())
    #cld.Show(la="cloud-join")
    
    #res=cld.GetPointsClosestClouds([rs.PointCoordinates(x) for x in rs.GetObjects("pick pts", rs.filter.point)],200)
    #for cld in res:
    #    cld.Show()

    
    #for x in rs.GetObjects("pick point-clouds"):
    #    cld=Cloud(cldguid=x)
    
    #cld=Cloud(cldguid=rs.GetObject("pick point-cloud"))
    #AELRC
    #res=cld.GetPointsClosestClouds([rs.CurveMidPoint(x) for x in rs.GetObjects("pick crv", rs.filter.curve)],200)
    #for cld in res:
    #   cld.Show()
    #res=cld.GetMeshClosestPoints(rs.GetObject("sel mesh as ref", rs.filter.mesh),100)
    #join=cld.Join(cldguid=rs.GetObjects("",rs.filter.pointcloud))
    #res.Show()
    
    #cld.Reduce(factor=0.1).Show("Join-Reduce-0.1")
    
    """
    mesh=rs.GetObject("mesh",rs.filter.mesh)
    clds=rs.GetObjects("sel clds", rs.filter.pointcloud)
    for c in clds:
        cld=Cloud(cldguid=c)
        res=cld.GetMeshClosestPointsQuartile(mesh,50,0.2,0.8)
        if res!=None:
            res.Show()
    """
    #END AELRC
    
    
    
    #cld.Reduce(factor=0.1).Show("Region04")
    #res=cld.GetPointsClosestClouds(rs.GetObjects("pick pt"),100)
    #res=cld.GetCurvesClosestPoints(rs.GetObjects("crvs",rs.filter.curve),200)
    #res=cld.GetBrepClosestPoints(rs.GetObject("brep", rs.filter.surface),100)
    
    
    #for cld in res:
    #    cld.Show()

    #cld.GetBrepClosestPoints(rs.GetObject("brep",rs.filter.surface),10).Show()
    #cld.GetCurvesClosestPoints(rs.GetObjects("crvs",rs.filter.curve),10).Show("networkX")
    
    #res=cld.GetPointsClosestClouds(rs.GetObjects("pick pt"),100)
    #for cld in res:
    #    cld.Show()
    
    #cld=cld.Reduce(factor=0.01).Show()
    #cld.Split(1000,1000,3000)
    #dmx=DistanceMatrix(cld.CLD)
    #cld.Show()
     


def test_evaluate():
    
    scale=10
    mesh=rs.GetObjects("mesh",rs.filter.mesh)
    clds=rs.GetObjects("sel clds", rs.filter.pointcloud)
    cguid=[]
    data=[]
    for c in clds:
        la=rs.ObjectLayer(c)
        lan=rs.AddLayer("eva",parent=la)
        cld=Cloud(cldguid=c)
        clomesh=rs.PointClosestObject(cld.CLD.Item[0].Location,mesh)[0]
        line=cld.BuildDeviationVectorToMesh(clomesh,scale=scale)
        
        if line!=None:
            clomeshcopy=rs.CopyObject(clomesh,(rs.CurveEndPoint(line)-rs.CurveStartPoint(line))/scale)
            linevec=rs.CurveEndPoint(line)-rs.CurveStartPoint(line)
            fak=1
            #ang=rs.VectorAngle(linevec,Rhino.Geometry.Vector3d.XAxis)
            if rs.VectorAngle(linevec,Rhino.Geometry.Vector3d.XAxis)>90:
                fak=-1
            linevec.Unitize()
            length=rs.CurveLength(line)
            sp=rs.CurveStartPoint(line)
            rs.DeleteObject(line)
            line=rs.AddLine(sp,sp+linevec*1000)
            rs.CurveArrows(line,2)
            #rs.MoveObject(line,rs.CurveStartPoint(line)-rs.CurveEndPoint(line))
            data.append(length*fak)
            dot=rs.AddTextDot(str(round(length/scale,1)),rs.CurveStartPoint(line))
            h=int(length/scale)/2
            if h<10:
                h=10
            rs.TextDotHeight(dot,h)
            #if fak<0:
            #    rs.SelectObject(clomeshcopy)
            cguid.append((dot,line,clomeshcopy))
            rs.ObjectLayer(cguid[-1],lan)
    
    for i,col in enumerate(viz.CalcColorValues(data)):
        rs.ObjectColor(cguid[i],col)
    
def viz_deviations():
    
    mesh=rs.GetObject("mesh",rs.filter.mesh)
    cld=rs.GetObject("sel clds", rs.filter.pointcloud)
    
    cld=Cloud(cldguid=cld)
    ccld,devs=cld.GetMeshClosestPoints(mesh)
    cld.ApplyColors(viz.CalcColorValues(devs))
    print min(devs)
    print max(devs)
    cld.Show(layer="vis_deviations")
    
def FitPlanes():
    la="FitPlanes"
    rs.AddLayer(la)
    while True:
        mesh=rs.GetObject("mesh",rs.filter.mesh)
        vertices=rs.GetMeshVertices(mesh)
        cm=rs.coercemesh(mesh)
        #mv=rs.MeshVertices(mesh)
        
        vx=[cm.Vertices[vertex] for vertex in vertices]
        pl=rs.PlaneFitFromPoints(vx)
        bbx=rs.BoundingBox(vx,pl)
        #rs.AddBox(bbx)
        pl.Origin=pl.ClosestPoint(bbx[0])
        rs.ObjectLayer(rs.AddPlaneSurface(pl,bbx[0].DistanceTo(bbx[1]),bbx[0].DistanceTo(bbx[3])),la)
        
    pass

def GenSections():
    
    clds=[Cloud(x) for x in rs.GetObjects("sel cloud to manipulate",rs.filter.pointcloud)]
    plsrfs=rs.GetObjects("pick planar surfaces", rs.filter.surface)    
    pls=[rs.PlaneFitFromPoints(rs.SurfaceEditPoints(plsrf)) for plsrf in plsrfs if rs.IsPlaneSurface(plsrf)]    
    
    for cld in clds:
        for i,plane in enumerate(pls):
            subcloud=cld.GetPlaneClosestCloud(plane=plane,threshold=100)
            subcloud.Show("section-{0:s}".format(rs.ObjectName(plsrfs[i])))

def test_extract():
    
    cld=Cloud(rs.GetObject("sel cloud to manipulate",rs.filter.pointcloud))
    
    res=cld.GetMeshClosestPoints(rs.GetObject("sel mesh as ref", rs.filter.mesh),8)[0]
    res.Show()
    
    pass

def test_extract_meshes():
    
    
    meshes=rs.GetObjects("sel meshes as ref", rs.filter.mesh)
    cld=Cloud(rs.GetObject("sel cloud to manipulate",rs.filter.pointcloud))
    for m in meshes:
        
    
    
        res=cld.GetMeshClosestPoints(m,10)[0]
        res.Show()
    
    pass


if __name__=="__main__":
    GenSections()
    #FitPlanes()
    #viz_deviations()
    #test_evaluate()
    #test_extract()
    #test_extract_meshes()
    #test()
    #debug()
