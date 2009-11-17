"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import cherrytemplate, sys

print "#"*20
print "# Running unittest for Python-%s and CherryTemplate-%s" % (
    sys.version.split()[0], cherrytemplate.__version__)
print "#"*20
print

def checkRes(res, expectedRes):
    if res != expectedRes:
        f = open('result', 'w')
        f.write("Result: " + repr(res) + "\n")
        f.close()
        f = open('result.raw', 'w')
        f.write(res)
        f.close()
        print "\nThe expected result was:\n%s and the real result was:\n%s\n*** ERROR ***" % (
            repr(expectedRes), repr(res))
        sys.exit(-1)
    print "OK"

print "Testing CGTL...",
name = "world"
res = cherrytemplate.renderTemplate(file = 'testTags.html')

checkRes(res, open('testTags.result', 'r').read())

print "Testing latin-1 template, latin-1 output (1)...",
europoundUnicode = u'\x80\xa3'
europoundLatin1 = europoundUnicode.encode('latin-1')
res = cherrytemplate.renderTemplate(europoundLatin1 + """<py-eval="europoundLatin1">""")
checkRes(res, europoundLatin1*2)

print "Testing latin-1 template, latin-1 output (2)...",
res = cherrytemplate.renderTemplate(europoundLatin1 + """<py-eval="europoundLatin1">""", inputEncoding = 'latin-1', outputEncoding = 'latin-1')
checkRes(res, europoundLatin1*2)

print "Testing latin-1 template, utf-16 output...",
res = cherrytemplate.renderTemplate(europoundLatin1 + """<py-eval="europoundLatin1">""", inputEncoding = 'latin-1', outputEncoding = 'utf-16')
checkRes(res, (europoundUnicode*2).encode('utf-16'))

print "Testing unicode template, latin-1 output...",
res = cherrytemplate.renderTemplate(europoundUnicode + """<py-eval="europoundUnicode">""", outputEncoding = 'latin-1')
checkRes(res, europoundLatin1*2)

print "Testing external latin-1 template, latin-1 output...",
res = cherrytemplate.renderTemplate(file = 't.html', inputEncoding = 'latin-1', outputEncoding = 'latin-1')
checkRes(res, europoundLatin1*2 + '\n')

print "Testing py-include...",
res = cherrytemplate.renderTemplate("""Hello, <py-include="t.html">""", inputEncoding = 'latin-1', outputEncoding = 'latin-1')
checkRes(res, "Hello, " + europoundLatin1*2 + '\n')

print "Testing generator result...",
template = """<py-for="i in xrange(10000)"><py-eval="str(i)"></py-for>"""
for i, line in enumerate(cherrytemplate.renderTemplate(template, returnGenerator = True)):
    try:
        assert int(line) == i
    except:
        print "\nError in returnGenerator template\n*** ERROR ***"
        sys.exit(-1)
    i += 1
assert(i == 10000)
print "OK"
