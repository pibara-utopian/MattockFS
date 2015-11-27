#!/usr/bin/python
#Copyright (c) 2015, Rob J Meijer.
#Copyright (c) 2015, University College Dublin
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without
#modification, are permitted provided that the following conditions are met:
#1. Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
#2. Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
#3. All advertising materials mentioning features or use of this software
#   must display the following acknowledgement:
#   This product includes software developed by the <organization>.
#4. Neither the name of the <organization> nor the
#   names of its contributors may be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY <COPYRIGHT HOLDER> ''AS IS'' AND ANY
#EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE
#
#This code constitutes a Python port of the CarvPath library. It is meant to be used
#by forensic tools and frameworks in the service of implementing zero-storage carving
#facilities or other processes where designation of of potentially fragmented and sparse 
#sub-entities is esential.
#
import copy
import os
import fcntl

try:
  from os import posix_fadvise,POSIX_FADV_DONTNEED,POSIX_FADV_NORMAL
except:
  try:  
    from fadvise import posix_fadvise,POSIX_FADV_DONTNEED,POSIX_FADV_NORMAL
  except:
    import sys
    print("")
    print("\033[93mERROR:\033[0m fadvise module not installed. Please install fadvise python module. Run:")
    print("")
    print("    sudo pip install fadvise")
    print("")
    sys.exit()
try:
    from pyblake2 import blake2b
    ohash_algo=blake2b
except ImportError:
    import sys
    print("")
    print("\033[93mERROR:\033[0m Pyblake2 module not installed. Please install blake2 python module. Run:")
    print("")
    print("    sudo pip install pyblake2")
    print("")
    sys.exit()
try:
    #When this was written, pyblake2 didn't implement blake2bp yet. Hopefully it does in the future so the
    #Python implementation can be close to as fast as, and compatible with, the C++ implementation.
    from pyblake2 import blake2bp
    ohash_algo=blake2bp
except:
    pass

class _Opportunistic_Hash:
  def __init__(self,size):
    self._h= ohash_algo(digest_size=32)
    self.offset=0
    self.isdone=False
    self.result="INCOMPLETE-OPPORTUNISTIC_HASHING"
    self.fullsize=size
  def sparse(self,length):
    _h.update(bytearray(length).decode())
  def written_chunk(self,data,offset):
    if offset < self.offset or self.isdone:
      self._h=ohash_algo(digest_size=32) #restart, we are no longer done, things are getting written.
      self.offset=0
      self.isdone=false
      self.result="INCOMPLETE-OPPORTUNISTIC_HASHING"
    if (offset > self.offset):
      #There is a gap!
      difference = offset - self.offset
      times = difference / 1024
      for i in range(0,times):
        self.sparse(1024)
        self.sparse(difference % 1024)
      if offset == self.offset:
        self._h.update(data)
        self.offset += len(data)  
  def read_chunk(self,data,offset):
    if (not self.isdone) and offset <= self.offset and offser+len(data) > self.offset:
      #Fragment overlaps our offset; find the part that we didn't process yet.
      start=self.offset - offset
      datasegment = data[start:]
      self._h.update(datasegment)
      self.offset += len(datasegment)
      if self.offset > 0 and self.offset == self.fullsize:
        self.done()
  def done(self):
    if not isdone:
      self.result=self._h.hexdigest()

class _OH_Entity:
  def __init__(self,ent):
    self.ent=copy.deepcopy(ent)
    self.ohash=_Opportunistic_Hash(self.ent.totalsize)
    self.roi=ent._getroi(0)
  def  written_parent_chunk(self,data,parentoffset):
    parentfragsize=len(data)
    #Quick range of interest check.
    if parentoffset < self.roi[1] and (parentoffset+parentfragsize) > self.roi[0]:
      childoffset=0
      working=False
      updated=False
      for fragment in self.ent.fragments:
        if (not fragment.issparse()) and parentoffset >= fragment.offset and parentoffset < fragment.offset + fragment.size:
          working=True
          realstart = fragment.offset 
          realend = fragment.offset+fragment.size
          if parentoffset > realstart:
            realstart = parentoffset
          if (parentoffset + parentfragsize) < realend:
            realend=parentoffset + parentfragsize
          if realend > realstart:
           relrealstart = realstart-parentoffset
           relrealend = realend-parentoffset
           self.ohash.written_chunk(data[relrealstart:relrealend],childoffset+realstart-fragment.offset)  
          updated=True
        else:
          if working and fragment.issparse():
            self.ohash.sparse(fragment.size)
          else:
            working=False
        childoffset+=fragment.size
      if updated:
        #Update our range of interest.
        self.roi=self.ent._getroi(self.ohash.offset)
  def  read_parent_chunk(self,data,parentoffset):
    parentfragsize=len(data)
    #Quick range of interest check.
    if (not self.ohash.isdone) and parentoffset < self.roi[1] and (parentoffset+parentfragsize) > self.roi[0]:
      childoffset=0
      working=False
      updated=False
      for fragment in self.ent.fragments:
        if (not fragment.issparse()) and parentoffset >= fragment.offset and parentoffset < fragment.offset + fragment.size:
          working=True
          realstart = fragment.offset
          realend = fragment.offset+fragment.size
          if parentoffset > realstart:
            realstart = parentoffset
          if (parentoffset + parentfragsize) < realend:
            realend=parentoffset + parentfragsize
          if realend > realstart:
           relrealstart = realstart-parentoffset
           relrealend = realend-parentoffset
           self.ohash.read_chunk(data[relrealstart:relrealend],childoffset+realstart-fragment.offset)
          updated=True
        else:
          if working and fragment.issparse():
            self.ohash.sparse(fragment.size)
          else:
            working=False
        childoffset+=fragment.size
      if updated:
        #Update our range of interest.
        self.roi=self.ent_getroi(self.ohash.offset)
  def hashing_offset(self):
    return self.ohash.offset
  def hashing_result(self):
    return self.ohash.result
  def hashing_isdone(self):
    return self.ohash.isdone
      
    

#A fragent represents a contiguous section of a higher level data entity.
class Fragment:
  #Constructor can either be called with a fragment carvpath token string or with an offset and size.
  #A fragment carvpath token string is formatted like '<offset>+<size>', for example : '2048+512'
  def __init__(self,a1,a2=None):
    if isinstance(a1,str):
      (self.offset,self.size) = map(int,a1.split('+'))
    else:
      self.offset=a1
      self.size=a2
  #Casting Fragment to a carvpath string
  def __str__(self):
    if self.size == 0:
      return "S0"
    return str(self.offset) + "+" + str(self.size)
  def __hash__(self):
    return hash(str(self))
  def __lt__(self,other):
    if self.offset != other.offset:
      return self.offset < other.offset
    return self.size < other.size
  def __gt__(self,other):
    return other < self
  def __eq__(self,other):
    return self.offset == other.offset and self.size == other.size
  def __ne__(self,other):
    return self.offset != other.offset or self.size != other.size
  def __le__(self,other):
    return not (self > other)
  def __ge__(self,other):
    return not (self < other)
  def getoffset(self):
    return self.offset
  #This is how we distinguis a fragment from a sparse description
  def issparse(self):
    #A zero size fragment will act as a sparse description!
    return self.size == 0
  #If needed we can grow a fragment; only do this with the last fragment in an entity
  def grow(self,sz):
    self.size+=sz

#A Sparse object represents a higher level sparse definition that can be thought of as
#empty space that has no immage on any lower level data.
class Sparse:
  #Constructor can either be called with a sparse carvpath token string or with a size.
  #A sparse carvpath token string has the form 'S<size>', for example: 'S8192'
  def __init__(self,a1):
    if isinstance(a1,str):
      self.size = int(a1[1:])
    else:
      self.size = a1
  #Casting to a carvpath string
  def __str__(self):
    return "S" + str(self.size)
  def __hash__(self):
    return hash(str(self))
  def __lt__(self,other):
    return self.size < other.size
  def __gt__(self,other):
    return self.size > other.size
  def __eq__(self,other):
    return self.size == other.size
  def __ne__(self,other):
    return self.size != other.size
  def __le__(self,other):
    return self.size <= other.size
  def __ge__(self,other):
    return not (self.size >= other.size)
  #Calling this method on a Sparse will throw an runtime exception.
  def getoffset(self):
    raise RuntimeError("Sparse doesn't have an offset")
  #This is how we distinguis a fragment from a sparse description
  def issparse(self):
    return True
  #If needed we can grow a sparse region; only do this with the last fragment in an entity
  def grow(self,sz):
    self.size+=sz

#Helper function for creating either a sparse region or a fragment from a carvpath fragment/sparse token.
def _asfrag(fragstring):
  if fragstring[0] == 'S':
    return Sparse(fragstring)
  else:
    rval = Fragment(fragstring)
    if rval.size == 0:
      return Sparse("S0")
    return rval

#An entity is an ordered  collection of Fragment and/or Sparse objects. Entities are the core concept within pycarvpath.
class _Entity:
  #An Entity constructor takes either a carvpath, a list of pre-made fragments or no constructor argument at all
  #if you wish to create a new empty Entity. You should probably not be instantiating your own _Entity objects.
  #Instead, create entities using the 'parse' method of a Contect object.
  #An _Entity carvpath consists of one or more Fragment and/or Sparse carvpath tokens seperated by a '_' character.
  #for example: '0+4096_S8192_4096+4096'
  def __init__(self,lpmap,maxfstoken,a1=None):
    self.longpathmap=lpmap
    self.maxfstoken=maxfstoken
    fragments=[]
    self.fragments=[]
    if isinstance(a1,str):
      #Any carvpath starting with a capital D must be looked up in our longtoken database
      if a1[0] == 'D':
        carvpath=self.longpathmap[a1]
      else:
        carvpath=a1
      #Apply the _asfrag helper function to each fragment in the carvpath and use it to initialize our fragments list
      fragments=map(_asfrag,carvpath.split("_"))
    else:
      if isinstance(a1,list):
        #Take the list of fragments as handed in the constructor
        fragments = a1
      else:
        if a1 == None: 
          #We are creating an empty zero fragment entity here
          fragments=[]
        else:
          raise TypeError('Entity constructor needs a string or list of fragments '+str(a1))
    self.totalsize=0
    for frag in fragments:
      self.unaryplus(frag)
  def _asdigest(self,path):
    rval = "D" + blake2b(path.encode(),digest_size=32).hexdigest()
    self.longpathmap[rval] = path
    return rval
  #If desired, invoke the _Entity as a function to get the fragments it is composed of.
  def __cal__(self):
    for index in range(0,len(self.fragments)):
      yield self.fragments[index]
  #You may use square brackets to acces specific fragments.
  def __getitem__(self,index):
    return self.fragments[index]
  #Grow the entity by extending on its final fragment or, if there are non, by creating a first fragment with offset zero.
  def grow(self,chunksize):
    if len(self.fragments) == 0:
      self.fragments.append(Fragment(0,chunksize))
    else:
      self.fragments[-1].grow(chunksize)
    self.totalsize+=chunksize
  #Casting to a carvpath string
  def __str__(self):
    #Anything of zero size is represented as zero size sparse region.
    if len(self.fragments) == 0:
      return "S0"
    #Apply a cast to string on each of the fragment and concattenate the result using '_' as join character.
    rval = "_".join(map(str,self.fragments))
    #If needed, store long carvpath in database and replace the long carvpath with its digest.
    if len(rval) > self.maxfstoken:
      return self._asdigest(rval)
    else:
      return rval
  def __hash__(self):
    return hash(str(self))
  def __lt__(self,other):
    if self.totalsize == 0 and other.totalsize > 0:
      return True
    if other.totalsize == 0:
      return False
    ownfragcount=len(self.fragments)
    otherfragcount=len(other.fragments)
    sharedfragcount=ownfragcount
    for index in range(0,sharedfragcount):
      if self.fragments[index].issparse() != other.fragments[index].issparse():
        return self.fragments[index].issparse()
      if (not self.issparse()):
        if self.fragments[index].offset != other.fragments[index].offset:
          return self.fragments[index].offset < other.fragments[index].offset
      if self.fragments[index].size != other.fragments[index].size:
        return self.fragments[index].size < other.fragments[index].size
    return False
  def __gt__(self,other):
    return other < self
  def __le__(self,other):
    return not (self > other)
  def __ge__(self,other):
    return not (self < other)
  def __eq__(self,other):
    if not isinstance(other,_Entity):
      return False
    if self.totalsize != other.totalsize:
      return False
    if len(self.fragments) != len(other.fragments):
      return False
    for index in range(0,len(self.fragments)):
      if self.fragments[index].issparse() != other.fragments[index].issparse():
        return False
      if (not self.fragments[index].issparse()) and self.fragments[index].offset != other.fragments[index].offset:
        return False
      if self.fragments[index].size != other.fragments[index].size:
        return False
    return True
  def __ne__(self,other):
    return not self == other
  #Python does not allow overloading of any operator+= ; this method pretends it does.
  def unaryplus(self,other):
    if isinstance(other,_Entity):
      #We can either append a whole Entity
      for index in range(0,len(other.fragments)):
        self.unaryplus(other.fragments[index])
    else :
      #Or a single fragment.
      #If the new fragment is directly adjacent and of the same type, we don't add it but instead we grow the last existing fragment. 
      if len(self.fragments) > 0 and self.fragments[-1].issparse() == other.issparse() and (other.issparse() or (self.fragments[-1].getoffset() + self.fragments[-1].size) == other.getoffset()):
        self.fragments[-1]=copy.deepcopy(self.fragments[-1])
        self.fragments[-1].grow(other.size)
      else:
        #Otherwise we append the new fragment.
        self.fragments.append(other)
      #Meanwhile we adjust the totalsize member for the entity.
      self.totalsize += other.size
  #Appending two entities together, merging the tails if possible.
  def __add__(self,other):
    #Express a+b in terms of operator+= 
    rval=_Entity(self.longpathmap,self.maxfstoken)
    rval.unaryplus(this)
    rval.unaryplus(other)
    return rval
  #Helper generator function for getting the per-fragment chunks for a subentity.
  #The function yields the parent chunks that fit within the offset/size indicated relative to the parent entity.
  def _subchunk(self,offset,size):
    #We can't find chunks beyond the parent total size
    if (offset+size) > self.totalsize:
      raise IndexError('Not within parent range')
    #We start of at offset 0 of the parent entity whth our initial offset and size. 
    start=0
    startoffset = offset
    startsize = size
    #Process each parent fragment
    for parentfrag in self.fragments:
      #Skip the fragments that fully exist before the ofset/size region we are looking for.
      if (start + parentfrag.size) > startoffset:
        #Determine the size of the chunk we need to process
        maxchunk = parentfrag.size + start - startoffset
        if maxchunk > startsize:
          chunksize=startsize
        else:
          chunksize=maxchunk
        #Yield the proper type of fragment
        if chunksize > 0:
          if parentfrag.issparse():
            yield Sparse(chunksize)
          else:
            yield Fragment(parentfrag.getoffset()+startoffset-start,chunksize)
          #Update startsize for the rest of our data
          startsize -= chunksize
        #Update the startoffset for the rest of our data
        if startsize > 0:
          startoffset += chunksize
        else:
          #Once the size is null, update the offset as to skip the rest of the loops
          startoffset=self.totalsize + 1
      start += parentfrag.size 
  #Get the projection of an entity as sub entity of an other entity.
  def subentity(self,childent):
    subentity=_Entity(self.longpathmap,self.maxfstoken)
    for childfrag in childent.fragments:
      if childfrag.issparse():
        subentity.unaryplus(childfrag)
      else:
        for subfrag in self._subchunk(childfrag.offset,childfrag.size):
          subentity.unaryplus(subfrag)
    return subentity
  #Python has no operator=, so we use assigtoself
  def assigtoself(self,other):
    self.fragments=other.fragments
    self.totalsize=other.totalsize
  #Strip the entity of its sparse fragments and sort itsd non sparse fragments.
  #This is meant to be used for reference counting purposes inside of the Box.
  def stripsparse(self):
    newfragment=_Entity(self.longpathmap,self.maxfstoken)
    nosparse=[]
    for i in range(len(self.fragments)):
      if self.fragments[i].issparse() == False:
        nosparse.append(self.fragments[i])
    fragments=sorted(nosparse)
    for i in range(len(fragments)):
      newfragment.unaryplus(fragments[i])
    self.assigtoself(newfragment)
  #Merge an other sorted/striped entity and return two entities: One with all fragments left unused and one with the fragments used
  #for merging into self.
  def merge(self,entity):
    rval=_merge_entities(self,entity)
    self.assigtoself(rval[0])
    return rval[1:]
  #Opposit of the merge function. 
  def unmerge(self,entity):
    rval=_unmerge_entities(self,entity)
    self.assigtoself(rval[0])
    return rval[1:]
  def overlaps(self,entity):
    test=lambda a,b: a and b
    return _fragapply(self,entity,test)
  def density(self,entity):
    t=lambda a,b: a and b
    r=_fragapply(self,entity,[t])
    rval= float(r[0].totalsize)/float(self.totalsize)
    return rval
  def _getroi(self,fromoffset):
    coffset=0
    start=None
    end=None
    for fragment in self.fragments:
      if (not fragment.issparse()) and fromoffset <= coffset+fragment.size:
        if coffset <= fromoffset:
          start=fragment.offset + fromoffset - coffset
          end=fragment.offset+fragment.size
        else:
          if start > fragment.offset:
            start=fragment.offset
          if end < fragment.offset+fragment.size:
            end=fragment.offset+fragment.size
      coffset+=fragment.size
    return [start,end]
  
#Helper functions for mapping merge and unmerge to the higher order _fragapply function.
def _merge_entities(ent1,ent2):
  selfbf = lambda a, b : a or b
  remfb = lambda a,b : a and b
  insfb = lambda a,b : (not a) and b
  return _fragapply(ent1,ent2,[selfbf,remfb,insfb])

def _unmerge_entities(ent1,ent2):
  selfbf = lambda a, b : a and (not b)
  remfb = lambda a,b : (not a) and b
  drpfb = lambda a,b : a and b
  return _fragapply(ent1,ent2,[selfbf,remfb,drpfb]) 

#Helper function for applying boolean lambda's to each ent1/ent2 overlapping or non-overlapping fragment
#and returning an Entity with all fragments that resolved to true for tha coresponding lambda.
def _fragapply(ent1,ent2,bflist):
    #If our third argument is a lambda, use it as test instead.
    if callable(bflist):
      test=bflist
      testmode=True
    else:
      test= lambda a,b: False
      testmode=False
    chunks=[]
    foreignfragcount = len(ent2.fragments)
    foreignfragindex = 0
    ownfragcount = len(ent1.fragments)
    ownfragindex=0
    masteroffset=0
    ownoffset=0
    ownsize=0
    ownend=0
    foreignoffset=0
    foreignsize=0
    foreignend=0
    discontinue = foreignfragcount == 0 and ownfragcount == 0
    #Walk through both entities at the same time untill we are done with all fragments and have no remaining size left.
    while not discontinue:
      #Get a new fragment from the first entity if needed and possible
      if ownsize == 0 and ownfragindex!= ownfragcount:
        ownoffset=ent1.fragments[ownfragindex].getoffset()
        ownsize=ent1.fragments[ownfragindex].size
        ownend=ownoffset+ownsize
        ownfragindex += 1
      #Get a new fragment from the second entity if needed and possible
      if foreignsize == 0 and foreignfragindex!= foreignfragcount:
        foreignoffset=ent2.fragments[foreignfragindex].getoffset()
        foreignsize=ent2.fragments[foreignfragindex].size
        foreignend=foreignoffset+foreignsize
        foreignfragindex += 1
      #Create an array of start and end offsets and sort them
      offsets=[]
      if ownsize >0:
        offsets.append(ownoffset)
        offsets.append(ownend)
      if foreignsize > 0:
        offsets.append(foreignoffset)
        offsets.append(foreignend)
      offsets=sorted(offsets)
      #Find the part we need to look at this time around the while loop
      firstoffset = offsets[0]
      secondoffset = offsets[1]
      if secondoffset == firstoffset:
        secondoffset = offsets[2]
      #Initialize boolens
      hasone=False
      hastwo=False
      #See if this chunk overlaps with either or both of the two entities.
      if ownsize >0 and ownoffset==firstoffset:
        hasone=True
      if foreignsize>0 and foreignoffset==firstoffset:
        hastwo= True
      fragsize = secondoffset - firstoffset
      #If needed, insert an extra entry indicating the false/false state.
      if firstoffset > masteroffset:
        if testmode:
          if test(False,False):
            return True
        else:
          chunks.append([masteroffset,firstoffset-masteroffset,False,False])
        masteroffset=firstoffset
      if testmode:
        if test(hasone,hastwo):
          return True
      else:
        #Than append the info of our (non)overlapping fragment
        chunks.append([firstoffset,fragsize,hasone,hastwo])
      #Prepare for the next time around the loop
      masteroffset=secondoffset
      if hasone:
        ownoffset=masteroffset
        ownsize-=fragsize
      if hastwo:
        foreignoffset=masteroffset
        foreignsize-=fragsize
      #Break out of the loop as soon as everything is done.
      if foreignfragindex == foreignfragcount and ownfragcount == ownfragindex and ownsize == 0 and foreignsize==0:
        discontinue=True
    if testmode:
      return False
    #Create an array with Entity objects, one per lambda.
    rval=[]
    for index in range(0,len(bflist)):
      rval.append(_Entity(ent1.longpathmap,ent1.maxfstoken))
    #Fill each entity with fragments depending on the appropriate lambda invocation result.
    for index in range(0,len(chunks)):
      off=chunks[index][0]
      size=chunks[index][1]
      oldown=chunks[index][2]
      oldforeign=chunks[index][3]
      for index2 in range(0,len(bflist)):
        if bflist[index2](oldown,oldforeign):
          rval[index2].unaryplus(Fragment(off,size))
    return rval

def _defaultlt(al1,al2):
  for index in range(0,len(al1)):
    if al1[index] < al2[index]:
      return True
    if al1[index] > al2[index]:
      return False
  return False

class _CustomSortable:
  def __init__(self,carvpath,ltfunction,arglist):
    self.carvpath=carvpath
    self.ltfunction=ltfunction
    self.arglist=[]
    for somemap in arglist:
      self.arglist.append(somemap[carvpath])
  def __lt__(self,other):
    return self.ltfunction(self.arglist,other.arglist)

class _Box:
  def __init__(self,lpmap,maxfstoken,fadvise,top):
    self.longpathmap=lpmap
    self.maxfstoken=maxfstoken
    self.fadvise=fadvise
    self.top=top #Top entity used for all entities in the box
    self.content=dict() #Dictionary with all entities in the box.
    self.entityrefcount=dict() #Entity refcount for handling multiple instances of the exact same entity.
    self.fragmentrefstack=[] #A stack of fragments with different refcounts for keeping reference counts on fragments.
    self.fragmentrefstack.append(_Entity(self.longpathmap,self.maxfstoken)) #At least one empty entity on the stack
    self.ohash=dict()
  def __str__(self):
    rval=""
    for index in range(0,len(self.fragmentrefstack)):
      rval += "   + L" +str(index) + " : " + str(self.fragmentrefstack[index]) + "\n"
    for carvpath in self.content:
      rval += "   * " +carvpath + " : " + str(self.entityrefcount[carvpath]) + "\n"
    return rval
  def __hash__(self):
    return hash(str(self))
  #Add a new entity to the box. Returns two entities: 
  # 1) An entity with all fragments that went from zero to one reference count.(can be used for fadvise purposes)
  # 2) An entity with all fragments already in the box before add was invoked (can be used for opportunistic hashing purposes).
  def add_batch(self,carvpath):
    if carvpath in self.entityrefcount.keys():
      self.entityrefcount[carvpath] += 1
      ent=self.content[carvpath]
      return [_Entity(self.longpathmap,self.maxfstoken),ent]
    else:
      ent=_Entity(self.longpathmap,self.maxfstoken,carvpath)
      self.ohash[carvpath]=_OH_Entity(ent)
      ent.stripsparse()
      ent=self.top.topentity.subentity(ent)
      self.content[carvpath]=ent
      self.entityrefcount[carvpath] = 1
      r= self._stackextend(0,ent)
      merged=r[0]
      for fragment in merged:
        self.fadvise(fragment.offset,fragment.size,True)
      return
  #Remove an existing entity from the box. Returns two entities:
  # 1) An entity with all fragments that went from one to zero refcount (can be used for fadvise purposes).
  # 2) An entity with all fragments still remaining in the box. 
  def remove_batch(self,carvpath):
    if not carvpath in self.entityrefcount.keys():
      raise IndexError("Carvpath "+carvpath+" not found in box.")    
    self.entityrefcount[carvpath] -= 1
    if self.entityrefcount[carvpath] == 0:
      ent=self.content.pop(carvpath)
      del self.entityrefcount[carvpath]
      del self.ohash[carvpath]
      r= self._stackdiminish(len(self.fragmentrefstack)-1,ent)
      unmerged=r[0]
      for fragment in unmerged:
        self.fadvise(fragment.offset,fragment.size,False) 
      return
  #Request a list of entities that overlap from the box that overlap (for opportunistic hashing purposes).
  def _overlaps(self,offset,size):
    ent=_Entity(self.longpathmap,self.maxfstoken)
    ent.unaryplus(Fragment(offset,size))
    rval=[]
    for carvpath in self.content:
      if self.content[carvpath].overlaps(ent):
        rval.append(carvpath)
    return rval
  def priority_customsort(self,params,ltfunction=_defaultlt,intransit=None,reverse=False):
    Rmap={}
    rmap={}
    omap={}
    dmap={}
    smap={}
    wmap={}
    arglist=[]
    startset=intransit
    if startset == None:
      startset=set(self.content.keys()) 
    stacksize=len(self.fragmentrefstack)
    for letter in params:
      if letter == "R":
        looklevel=stacksize-1
        for index in range(looklevel,0,-1):
          hrentity=self.fragmentrefstack[index]
          for carvpath in startset:
            if hrentity.overlaps(self.content[carvpath]):
              Rmap[carvpath]=True 
            else:
              Rmap[carvpath]=False
          if len(Rmap)!=0 :
              break
        arglist.append(Rmap) 
      else:
        if letter == "r":
          if stacksize == 1:
            hrentity=self.fragmentrefstack[0]
            for carvpath in startset:
              if hrentity.overlaps(self.content[carvpath]):
                rmap[carvpath]=True
              else:
                rmap[carvpath]=False
            if len(rmap)!=0 :
              break
          else:
            for index in range(1,stacksize):
              f=lambda a,b: a and not b
              r=_fragapply(self.fragmentrefstack[index-1],self.fragmentrefstack[index],[f])
              hrentity=r[0]
              for carvpath in startset:
                if hrentity.overlaps(self.content[carvpath]):
                  rmap[carvpath]=True
                else:
                  rmap[carvpath]=False 
              if len(rmap)!=0 :
                break
          arglist.append(rmap)        
        else :
          if letter == "O":
            for carvpath in startset:
              offset=None
              for frag in self.content[carvpath].fragments:
                if offset==None or frag.issparse == False and frag.offset < offset:
                  offset=frag.offset
              omap[carvpath]=offset
            arglist.append(omap)
          else:
            if letter == "D":
              looklevel=stacksize-1
              for index in range(looklevel,0,-1):
                hrentity=self.fragmentrefstack[index]
                for carvpath in startset:
                  if hrentity.overlaps(self.content[carvpath]):
                    dmap[carvpath]=self.content[carvpath].density(hrentity)
              arglist.append(dmap)
            else:
              if letter == "S":
                for carvpath in startset:
                  smap[carvpath]=self.content[carvpath].totalsize
                arglist.append(smap)
              else:
                if letter == "W":
                  for carvpath in startset:
                    accumdensity=0
                    for index in range(0,len(self.fragmentrefstack)):
                       accumdensity+=self.content[carvpath].density(self.fragmentrefstack[index])
                    wmap[carvpath]=accumdensity
                  arglist.append(wmap)
                else:
                  raise RuntimeError("Invalid letter for pickspecial policy")
    sortable=[]
    for carvpath in startset:
      sortable.append(_CustomSortable(carvpath,ltfunction,arglist))
    sortable.sort(reverse=reverse)
    for wrapper in sortable:
      yield wrapper.carvpath
  def priority_customsorted(self,params,ltfunction=_defaultlt,intransit=None,reverse=False):
    customsrt=[]
    for entity in self.priority_customsort(params,ltfunction,intransit,reverse):
      customsrt.append(entity)
    return customsrt
  def priority_custompick(self,params,ltfunction=_defaultlt,intransit=None,reverse=False):
    for entity in self.priority_customsort(self,params,ltfunction,intransit,reverse):
      return entity #A bit nasty but safes needles itterations.
  def _stackextend(self,level,entity):
    if not (level < len(self.fragmentrefstack)):
      self.fragmentrefstack.append(_Entity(self.longpathmap,self.maxfstoken))
    ent=self.fragmentrefstack[level]
    res=ent.merge(entity)
    merged=res[1]
    unmerged=res[0]
    if (len(unmerged.fragments)!=0) :
      self._stackextend(level+1,unmerged)  
    return [merged,unmerged]
  def _stackdiminish(self,level,entity):
    ent=self.fragmentrefstack[level]
    res=ent.unmerge(entity)
    unmerged=res[1]
    remaining=res[0]
    if len(self.fragmentrefstack[level].fragments) == 0:
      self.fragmentrefstack.pop(level)
    if len(remaining.fragments) > 0:
      if level == 0:
        raise RuntimeError("Data remaining after _stackdiminish at level 0")    
      res2=self._stackdiminish(level-1,remaining)
      unmerged.merge(res2[1])
      return [res2[1],unmerged]
    else:
      if level == 0:
        return [unmerged,remaining]
      else:
        return [remaining,unmerged];
  def lowlevel_writen_data(self,offset,data):
    for carvpath in keys(self.ohash):
      self.ohash[carvpath].written_parent_chunk(data,offset)
  def lowlevel_read_data(self,offset,data):
    for carvpath in keys(self.ohash):
      self.ohash[carvpath].read_parent_chunk(data,offset)
  def batch_hashing_isdone(self,carvpath):
    return self.ohash[carvpath].hashing_isdone()
  def batch_hashing_value(self,carvpath):
    return self.ohash[carvpath].hashing_result()
  def batch_hashing_offset(self,carvpath):
    return self.ohash[carvpath].hashing_offset()


#This object allows an Entity to be validated against an underlying data source with a given size.
class _Top:
  #Don instantiate a _Top, Instantiate a Context and use Context::make_top instead.
  def __init__(self,lpmap,maxfstoken,size=0):
    self.size=size
    self.topentity=_Entity(lpmap,maxfstoken,[Fragment(0,size)])
  #Get this Top object as an Entity.
  def entity():
    return self.topentity
  #Make a Box object. Most likely you don't need one if you are implementing a forensic tool, as Box is 
  #meant primary to be used by the Repository implementation.
  def make_box(fadvise):
    return _Box(self.topentity.longpathmap,self.topentity.maxfstoken,fadvise,self.topentity)
  #If the underlying data source changes its size by data being added, grow allows you to notify the Top object of this
  #and allow future entities to exist within the extended bounds.
  def grow(self,chunk):
    self.size +=chunk
    self.topentity.grow(chunk)
  #Test if a given Entity is valid within the bounds of the Top data size.
  def test(self,child):
    try:
      b=self.topentity.subentity(child)
    except IndexError:
      return False
    return True

class _FadviseFunctor:
  def __init__(self,fd):
    self.fd=fd
  def __call__(self,offset,size,willneed):
    if willneed:
      posix_fadvise(self.fd,offset,size,POSIX_FADV_NORMAL)
    else:
      posix_fadvise(self.fd,offset,size,POSIX_FADV_DONTNEED)

class _RaiiFLock:
  def __init__(self,fd):
    self.fd=fd
    fcntl.flock(self.fd,fcntl.LOCK_EX)
  def __del__(self):
    fcntl.flock(self.fd,fcntl.LOCK_UN)

class _Repository:
  def __init__(self,reppath,lpmap,maxfstoken=160):
    self.lpmap=lpmap
    self.maxfstoken=maxfstoken
    self.fd=os.open(reppath,(os.O_RDWR | os.O_LARGEFILE | os.O_NOATIME | os.O_CREAT))
    cursize=os.lseek(self.fd,0,os.SEEK_END) 
    posix_fadvise(self.fd,0,cursize,POSIX_FADV_DONTNEED)
    self.top=_Top(lpmap,maxfstoken,cursize)
    fadvise=_FadviseFunctor(self.fd)
    self.box=_Box(lpmap,maxfstoken,fadvise,self.top)
  def __del__(self):
    os.close(self.fd)
  def _grow(self,newsize):
    l=_RaiiFLock(self.fd)
    os.ftruncate(self.fd,newsize)
  def newmutable(self,chunksize):
    chunkoffset=self.top.size
    self._grow(chunkoffset+chunksize) 
    self.top.grow(chunksize)
    cp=str(_Entity(self.lpmap,self.maxfstoken,[Fragment(chunkoffset,chunksize)])) 
    self.box.add_batch(cp)
    return cp
  def volume(self):
    if len(self.box.fragmentrefstack) == 0:
      return 0
    return self.box.fragmentrefstack[0].totalsize
    
  

#You need one of these per application in order to use pycarvpath.
class Context:
  #A Context needs a dict like object that implements persistent (and possibly distributed) storage of
  #long path entities and their shorter representation. This pseudo dict is passed as lpmap argument.
  #By default all carvpath strings larger than 160 bytes are represented by a 65 byte long token
  #stored in this pseudo dict. You may specify a different maximum carvpath lengt if you wish for a longer or
  #shorter treshold.
  def __init__(self,lpmap,maxtokenlen=160):
    self.longpathmap=lpmap
    self.maxfstoken=maxtokenlen
  #Parse a (possibly nested) carvpath and return an Entity object. This method will throw if a carvpath
  #string is invalid. It will however NOT set any upper limits to valid carvpaths within a larger image.
  #If you wish to do so, create a Top object and invoke Top::test(ent) with the Entity you got back from parse.
  def parse(self,path):
    levelmin=None
    for level in path.split("/"):
      level=_Entity(self.longpathmap,self.maxfstoken,level)
      if not levelmin == None:
        level = levelmin.subentity(level)
      levelmin = level
    return level
  #Cheate a Top object to validate parsed entities against.
  def make_top(self,size=0):
    return _Top(self.longpathmap,self.maxfstoken,size)
  #NOTE: This method should only be used in forensic filesystem or forensic framework implementations.
  #Open a raw repository file and make it accessible through a _Repository interface.
  def open_repository(self,rawdatapath):
    return _Repository(rawdatapath,self.longpathmap,self.maxfstoken)

class _Test:
  def __init__(self,lpmap,maxtokenlen):
    self.context=Context(lpmap,maxtokenlen)
  def testadd(self,pin1,pin2,pout):
    a=self.context.parse(pin1)
    b=self.context.parse(pin2)
    c=self.context.parse(pout)
    a.unaryplus(b)
    if (a!=c):
      print("FAIL: '" + pin1 + " + " + pin2 + " = " + str(a) +  "' expected='" + pout + "'")
    else:
     print("OK: '" + pin1 + " + " + pin2 + " = " + str(a) +  "'")
  def teststripsparse(self,pin,pout):
    a=self.context.parse(pin)
    b=self.context.parse(pout)
    a.stripsparse()
    if a != b:
      print("FAIL: in='" + pin + "' expected='" + pout + "' result='" + str(a) + "'")
    else:
      print("OK: in='" + pin + "' expected='" + pout + "' result='" + str(a) + "'")
  def testflatten2(self,context,pin,pout):
    a=context.parse(pin)
    b=context.parse(pout)
    if a != b:
      print("FAIL: in='" + pin + "' expected='" + pout + "  (" +str(b) +  ") ' result='" + str(a) + "'")
    else:
      print("OK: in='" + pin + "' expected='" + pout + "' result='" + str(a) + "'")
  def testflatten(self,context,pin,pout):
    a=context.parse(pin)
    if str(a) != pout:
      print("FAIL: in='" + pin + "' expected='" + pout + "' result='" + str(a) + "'")
    else:
      print("OK: in='" + pin + "' expected='" + pout + "' result='" + str(a) + "'")
    self.testflatten2(context,pin,pout)
  def testrange(self,topsize,carvpath,expected):
    context=Context({})
    top=context.make_top(topsize)
    entity=context.parse(carvpath)
    if top.test(entity) != expected:
      print("FAIL: topsize="+str(topsize)+"path="+carvpath+"result="+str(not expected))
    else:
      print("OK: topsize="+str(topsize)+"path="+carvpath+"result="+str(expected))
  def testsize(self,context,pin,sz):
    print("TESTSIZE:")
    a=context.parse(pin)
    if a.totalsize != sz:
      print("FAIL: in='" + pin + "' expected='" + str(sz) + "' result='" + str(a.totalsize) + "'")
    else:
      print("OK: in='" + pin + "' expected='" + str(sz) + "' result='" + str(a.totalsize) + "'")
  def testmerge(self,p1,p2,pout):
    print("TESTMERGE:")
    context=Context({})
    a=context.parse(p1)
    a.stripsparse()
    b=context.parse(p2)
    b.stripsparse()
    c=context.parse(pout)
    d=a.merge(b)
    if a!=c:
      print("FAIL : "+str(a)+"  "+str(d[0]) + " ;  "+str(d[1]))
    else:
      print("OK : "+str(a))
  def testrepository(self):
    print("TESTREPOSITORY:")
    context=Context({})
    repository=context.open_repository("/tmp/rep.dd")
    m1=repository.newmutable(100000000)
    m2=repository.newmutable(20000000)
    m3=repository.newmutable(3000000)
    m4=repository.newmutable(400000)
    m5=repository.newmutable(50000)
    m6=repository.newmutable(6000)
    m7=repository.newmutable(700)
    m8=repository.newmutable(80)
    m9=repository.newmutable(9)
    print("New mutable: "+m1)
    print("New mutable: "+m2)
    print("New mutable: "+m3)
    print("New mutable: "+m4)
    print("New mutable: "+m5)
    print("New mutable: "+m6)
    print("New mutable: "+m7)
    print("New mutable: "+m8)
    print("New mutable: "+m9)
if __name__ == "__main__":
  context=Context({})
  t=_Test({},160)
  t.testflatten(context,"0+0","S0");
  t.testflatten(context,"S0","S0");
  t.testflatten(context,"0+0/0+0","S0");
  t.testflatten(context,"20000+0","S0");
  t.testflatten(context,"20000+0_89765+0","S0");
  t.testflatten(context,"1000+0_2000+0/0+0","S0");
  t.testflatten(context,"0+5","0+5");
  t.testflatten(context,"S1_S1","S2");
  t.testflatten(context,"S100_S200","S300");
  t.testflatten(context,"0+20000_20000+20000","0+40000");
  t.testflatten(context,"0+20000_20000+20000/0+40000","0+40000");
  t.testflatten(context,"0+20000_20000+20000/0+30000","0+30000");
  t.testflatten(context,"0+20000_20000+20000/10000+30000","10000+30000");
  t.testflatten(context,"0+20000_40000+20000/10000+20000","10000+10000_40000+10000");
  t.testflatten(context,"0+20000_40000+20000/10000+20000/5000+10000","15000+5000_40000+5000");
  t.testflatten(context,"0+20000_40000+20000/10000+20000/5000+10000/2500+5000","17500+2500_40000+2500");
  t.testflatten(context,"0+20000_40000+20000/10000+20000/5000+10000/2500+5000/1250+2500","18750+1250_40000+1250");
  t.testflatten(context,"0+20000_40000+20000/10000+20000/5000+10000/2500+5000/1250+2500/625+1250","19375+625_40000+625");
  t.testflatten(context,"0+100_101+100_202+100_303+100_404+100_505+100_606+100_707+100_808+100_909+100_1010+100_1111+100_1212+100_1313+100_1414+100_1515+100_1616+100_1717+100_1818+100_1919+100_2020+100_2121+100_2222+100_2323+100_2424+100","D901141262aa24eaaddbce2f470615b6a47639f7a62b3bc7c65335251fe3fa480");
  t.testflatten(context,"0+100_101+100_202+100_303+100_404+100_505+100_606+100_707+100_808+100_909+100_1010+100_1111+100_1212+100_1313+100_1414+100_1515+100_1616+100_1717+100_1818+100_1919+100_2020+100_2121+100_2222+100_2323+100_2424+100/1+2488","D0e2ded6b35aa15baabd679f7d8b0a7f0ad393948988b6b2f28db7c283240e3b6");
  t.testflatten(context,"D901141262aa24eaaddbce2f470615b6a47639f7a62b3bc7c65335251fe3fa480/1+2488","D0e2ded6b35aa15baabd679f7d8b0a7f0ad393948988b6b2f28db7c283240e3b6");
  t.testflatten(context,"D901141262aa24eaaddbce2f470615b6a47639f7a62b3bc7c65335251fe3fa480/350+100","353+50_404+50");
  t.testflatten(context,"S200000/1000+9000","S9000")

  t.testrange(200000000000,"0+100000000000/0+50000000",True)
  t.testrange(20000,"0+100000000000/0+50000000",False)
  t.testsize(context,"20000+0_89765+0",0)
  t.testsize(context,"0+20000_40000+20000/10000+20000/5000+10000",10000)
  t.testsize(context,"D901141262aa24eaaddbce2f470615b6a47639f7a62b3bc7c65335251fe3fa480/350+100",100)
  t.teststripsparse("0+1000_S2000_1000+2000","0+3000")
  t.teststripsparse("1000+2000_S2000_0+1000","0+3000")
  t.teststripsparse("0+1000_S2000_4000+2000","0+1000_4000+2000")
  t.teststripsparse("4000+2000_S2000_0+1000","0+1000_4000+2000")
  t.testadd("0+1000_S2000_1000+2000","3000+1000_6000+1000","0+1000_S2000_1000+3000_6000+1000")
  t.testadd("0+1000_S2000","S1000_3000+1000","0+1000_S3000_3000+1000")
  t.testmerge("0+1000_2000+1000","500+2000","0+3000")
  t.testmerge("2000+1000_5000+100","100+500_800+800_4000+200_6000+100_7000+100","100+500_800+800_2000+1000_4000+200_5000+100_6000+100_7000+100")
  t.testmerge("2000+1000_5000+1000","2500+500","2000+1000_5000+1000")
  t.testmerge("500+2000","0+1000_2000+1000","0+3000")
  t.testmerge("0+1000_2000+1000","500+1000","0+1500_2000+1000")
  t.testmerge("S0","0+1000_2000+1000","0+1000_2000+1000")
  t.testmerge("0+60000","15000+30000","0+60000")
  t.testrepository()
   