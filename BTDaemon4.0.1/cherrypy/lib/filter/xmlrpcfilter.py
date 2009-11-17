"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
##########################################################################
## Remco Boerma
##
## History:
## 1.0.0   : 2004-12-29 Released with CP2
## 0.0.9   : 2004-12-23 made it CP2 #59 compatible (returns an iterable)
##           Please note: as the xmlrpc doesn't know what you would want to return
##           (and for the logic of marshalling) it will return Generator objects, as
##           it is.. So it'll brake on that one!!
##           NOTE: __don't try to return a Generator object to the caller__
##           You could of course handle the generator usage internally, before sending
##           the result. This breaks from the general cherrypy way of handling generators...
## 0.0.8   : 2004-12-23 cpg.request.paramList should now be a filter. 
## 0.0.7   : 2004-12-07 inserted in the experimental branch (all remco boerma till here)
## 0.0.6   : 2004-12-02 Converted basefilter to baseinputfileter,baseoutputfilter
## 0.0.5   : 2004-11-22 "RPC2/" now changed to "/RPC2/" with the new mapping function
##           Gian paolo ciceri notified me with the lack of passing parameters.
##           Thanks Gian, it's now implemented against the latest trunk.
##           Gian also came up with the idea of lazy content-type checking: if it's sent
##           as a header, it should be 'text/xml', if not sent at all, it should be
##           accepted. (While this it not the xml/rpc standard, it's handy for those
##           xml-rpc client implementations wich don't send this header)
## 0.0.4   : 2004-11-20 in setting the path, the dot is replaces by a slash
##           therefore the regular CP2 routines knows how to handle things, as 
##           dots are not allowed in object names, it's varely easily adopted. 
##           Path + method handling. The default path is 'RPC2', this one is 
##           stripped. In case of path 'someurl' it is used for 'someurl' + method
##           and 'someurl/someotherurl' is mapped to someurl.someotherurl + method.
##           this way python serverproxies initialised with an url other than 
##           just the host are handled well. I don't hope any other service would map
##           it to 'RPC2/someurl/someotherurl', cause then it would break i think. .
## 0.0.3   : 2004-11-19 changed some examples (includes error checking 
##           wich returns marshalled Fault objects if the request is an RPC call.
##           took testing code form afterRequestHeader and put it in 
##           testValidityOfRequest to make things a little simpler. 
##           simply log the requested function with parameters to stdout
## 0.0.2   : 2004-11-19 the required cgi.py patch is no longer needed
##           (thanks remi for noticing). Webbased calls to regular objects
##           are now possible again ;) so it's no longer a dedicated xmlrpc
##           server. The test script is also in a ready to run file named 
##           testRPC.py along with the test server: filterExample.py
## 0.0.1   : 2004-11-19 informing the public, dropping loads of useless
##           tests and debugging
## 0.0.0   : 2004-11-19 initial alpha
## 
##---------------------------------------------------------------------
## 
## EXAMPLE CODE FOR THE SERVER:
##    from cherrypy import cpg
##    import cherrypy.lib.xmlrpcfilter as xmlrpcfilter
##    class Root:
##        _cpFilterList = [xmlrpcfilter.XmlRpcFilter()] 
##
##        def test(self):
##            return `"I'm here"`
##        test.exposed = True
##    cpg.root = Root()
##    cpg.server.start()
##        
## EXAMPLE CODE FOR THE CLIENT:
##    import xmlrpclib
##    server = xmlrpclib.ServerProxy('http://localhost:8080')
##    print server.test()
##    # results in: "I'm here"
## 
######################################################################

from basefilter import BaseInputFilter, BaseOutputFilter
from cherrypy import cpg
import xmlrpclib


class XmlRpcFilter(BaseInputFilter,BaseOutputFilter):
    """
    Derivative of basefilter.
    Test to convert XMLRPC to CherryPy2 object system and reverse

    PLEASE NOTE:

    afterRequestHeader:
        Unmarshalls the posted data to a methodname and parameters.
            - These are stored in cpg.request.rpcMethod and cpg.request.rpcParams
            - The method is also stored in cpg.request.path, so CP2 will find the right
              method to call for you. Based on the root's position
    beforeResponse:
        Marshalls the result of the excecuted function (in cpg.response.body) to xmlrpc.
            - Until resolved: the result must be a python souce string with the results,
              this string is 'eval'ed to return the results. This will be resolved in the
              future.
            - the Content-Type and -Length are set according to the new (marshalled) data. 
              

    """
    def testValidityOfRequest(self):
        # test if the content-length was sent
        result = int(cpg.request.headerMap.get('Content-Length',0)) > 0
        result = result and cpg.request.headerMap.get('Content-Type','text/xml').lower() in ['text/xml']
        return result
        
    def afterRequestHeader(self):
        """ Called after the request header has been read/parsed"""
        cpg.request.isRPC = self.testValidityOfRequest()
        if not cpg.request.isRPC: 
            # used for debugging or more info
            # print 'not a valid xmlrpc call'
            return # break this if it's not for this filter!!
        # used for debugging, or more info:
        # print "xmlrpcmethod...",
        cpg.request.parsePostData = 0
        dataLength = int(cpg.request.headerMap.get('Content-Length',0))
        data = cpg.request.rfile.read(dataLength)
        try:
            params, method = xmlrpclib.loads(data)
        except Exception,e: 
            params, method =  ('ERROR PARAMS',),'ERRORMETHOD'
        cpg.request.rpcMethod, cpg.request.rpcParams = method,params
        # patch the path. .there are only a few options:
        # - 'RPC2' + method >> method
        # - 'someurl' + method >> someurl.method
        # - 'someurl/someother' + method >> someurl.someother.method
        if not cpg.request.path.endswith('/'):
            cpg.request.path+='/'
        if cpg.request.path.startswith('/RPC2/'):
            cpg.request.path=cpg.request.path[5:] ## strip the irst /rpc2
        cpg.request.path+=str(method).replace('.','/')
        cpg.request.paramList = list(params)
        # used for debugging and more info
        # print "XMLRPC Filter: calling '%s' with args: '%s' " % (cpg.request.path,params)

    def beforeResponse(self):
        """ Called before starting to write response """
        if not cpg.request.isRPC: 
            return # it's not an RPC call, so just let it go with the normal flow
        try:
            # use this for debugging and more info:
            # print 'beforeResponse: cpg.response.body ==',`cpg.response.body` 
            cpg.response.body = xmlrpclib.dumps((cpg.response.body[0],), methodresponse=1,allow_none=1)
        except xmlrpclib.Fault,fault:
            cpg.response.body = xmlrpclib.dumps(fault,allow_none=1)
        except Exception,e:
            print 'EXCEPTION: ',e
        cpg.response.headerMap['Content-Type']='text/xml'
        cpg.response.headerMap['Content-Length']=`len(cpg.response.body)`

