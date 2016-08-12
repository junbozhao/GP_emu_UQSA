### for the underlying sensistivity classes

import numpy as np
import matplotlib.pyplot as plt

class Sensitivity:
    def __init__(self, emul, m, v):
        print("This is the Sensitivity class being initialised")

        ## inputs stuff
        self.v = v
        self.m = m
        self.x = emul.training.inputs
        
        ## try to use exact values on the MUCM site
        #if True:
        if False:
            emul.par.delta = [[[ 0.5437, 0.0961 ]]]
            emul.par.sigma[0][0] = np.sqrt(0.9354)
            emul.par.sigma[0][0] = np.sqrt(0.92439104)
            emul.par.beta = np.array([ 33.5981 , 4.8570 , -39.6695 ])
            emul.training.remake()

        #### init B
        self.B = np.linalg.inv(np.diag(self.v))
        print("B matrix:\n", self.B)

        #### init C
        self.C = np.diag( 1.0/(np.array(emul.par.delta[0][0])**2) )
        print("C matrix:\n", self.C)

        #### save these things here for convenience
        self.f = emul.training.outputs
        self.H = emul.training.H
        self.beta = emul.par.beta
        self.sigma = emul.par.sigma[0][0] ## only taking the first sigma
        self.A = emul.training.A ## my A has sigma**2 absorbed into it...

        #### calculate the unchanging matrices (not dep. on w)
        self.UPSQRT_const()
       
        #### calculate some other unchanging quantities
        self.e = np.linalg.solve(\
            self.A/(self.sigma**2), (self.f - self.H.dot(self.beta)) )
        self.W = np.linalg.inv( (self.H.T)\
            .dot(np.linalg.solve(self.A/(self.sigma**2), self.H)  ) )
        self.G = np.linalg.solve(self.A, self.H)


    def uncertainty(self):
        # for the uncertainty analysis
        
        ## let w be the entire set for now
        self.w = [0, 1, 2]

        ############# R integrals #############
        self.Rh = np.append([1.0], np.array(self.m[self.w]))
        print("Rh:" , self.Rh)

        self.Rhh = np.zeros([ 1+len(self.w) , 1+len(self.w) ])
        self.Rhh[0][0] = 1.0
        # fill first row and column
        for i in self.w:
            self.Rhh[0][1+i] = self.m[i]
            self.Rhh[1+i][0] = self.m[i]

        mw_mw = np.outer( self.m[self.w] , self.m[self.w].T )
        Bww = np.diag( np.diag(self.B)[self.w] )
        mw_mw_Bww = mw_mw + np.linalg.inv(Bww)
        #print( "m(w)m(w)^T + invBww :", mw_mw_Bww )
        for i in range(0,len(self.w)):
            for j in range(0,len(self.w)):
                self.Rhh[1+self.w[i]][1+self.w[j]] = mw_mw_Bww[i][j]
        print("Rhh:\n",self.Rhh)

        ## !!!! code currently only works when self.w is complete set !!!!
        #self.Qk = np.zeros([self.x[:,0].size])
        self.Rt = np.zeros([self.x[:,0].size])
        self.Rht = np.zeros([1+len(self.w) , self.x[:,0].size])
        for k in range(0, self.x[:,0].size):
            mpk = np.linalg.solve(\
            2.0*self.C+self.B , 2.0*self.C.dot(self.x[k]) + self.B.dot(self.m) )
            #print("m'k:\n" , mpk)
            Qk = 2.0*(mpk-self.x[k]).T.dot(self.C).dot(mpk-self.x[k])\
                  + (mpk-self.m).T.dot(self.B).dot(self.x[k]-self.m)
            self.Rt[k] = np.sqrt(\
                np.linalg.det(self.B)/np.linalg.det(2.0*self.C+self.B))*\
                np.exp(-0.5*Qk)
            Ehx = np.append([1.0], mpk)
            self.Rht[:,k] = self.Rt[k] * Ehx
        print("Rt:\n" , self.Rt)
        print("Rht:\n" , self.Rht)

        
        #self.Qkl = np.zeros([self.x[:,0].size])
        self.Rtt = np.zeros([self.x[:,0].size , self.x[:,0].size])
        for k in range(0, self.x[:,0].size):
            for l in range(0, self.x[:,0].size):
                mpkl = np.linalg.solve(\
                    4.0*self.C+self.B ,\
                    2.0*self.C.dot(self.x[k]) + 2.0*self.C.dot(self.x[l])\
                    + self.B.dot(self.m) )
                Qkl = 2.0*(mpkl-self.x[k]).T.dot(self.C).dot(mpkl-self.x[k])\
                           + 2.0*(mpkl-self.x[l]).T.dot(self.C).dot(mpkl-self.x[l])\
                           + (mpkl-self.m).T.dot(self.B).dot(self.x[k]-self.m)
                self.Rtt[k,l] = np.sqrt(\
                    np.linalg.det(self.B)/np.linalg.det(4.0*self.C+self.B))*\
                    np.exp(-0.5*Qkl)
        print("Rtt:\n" , self.Rtt)

        ############# U integrals #############


    def main_effect(self):
        # for storing the effect
        points = 21
        self.effect = np.zeros([self.m.size , points])

        #### initialise the w matrices
        self.Tw=np.zeros([self.x[:,0].size])
        self.Rw=np.zeros([1+1])
        self.Qw=np.zeros([1+len(self.m) , 1+len(self.m)])
        self.Sw=np.zeros([1+len(self.m) , self.x[:,0].size ])
        self.Pw=np.zeros([self.x[:,0].size , self.x[:,0].size])
        self.Uw=0.0

        for P in range(0,len(self.m)):
            print("Sensitivity measures for input", P)
            self.w = [P]
            self.wb = []
            for k in range(0,len(self.m)):
                if k not in self.w:
                    self.wb.append(k)

            j = 0 ## j just counts index for each value of xw we try
            for self.xw in np.linspace(0.0,1.0,points): ## changes value of xw

                self.UPSQRT(self.w , self.xw)

                self.Emw = self.Rw.dot(self.beta) + self.Tw.dot(self.e)
                self.ME = (self.Rw-self.R).dot(self.beta)\
                    + (self.Tw-self.T).dot(self.e)
                #print("xw:",self.xw,"ME_",self.w,":",self.ME)
                self.effect[self.w, j] = self.ME
                j=j+1 ## calculate for next xw value

            plt.plot( np.linspace(0.0,1.0,points), self.effect[P] ,\
                linewidth=2.0, label='x'+str(P) )
        plt.legend(loc='best')
        plt.show()


    def sensitivity(self):
        print("\n*** Calculate sensitivity indices ***")
        self.senseindex = np.zeros([self.m.size])

        #### initialise the w matrices
        self.Tw=np.zeros([self.x[:,0].size])
        self.Qw=np.zeros([1+len(self.m) , 1+len(self.m)])
        self.Sw=np.zeros([1+len(self.m) , self.x[:,0].size ])
        self.Pw=np.zeros([self.x[:,0].size , self.x[:,0].size])
        ## these get redefined anyway
        self.Rw=np.zeros([1+1]) ## for when w is a single index
        self.Uw=0.0

        for P in range(0,len(self.m)):
            print("Sensitivity measures for input", P)
            self.w  = [P]
            self.wb = []
            for k in range(0,len(self.m)):
                if k not in self.w:
                    self.wb.append(k)
            self.xw = self.m[P]
            self.UPSQRT(self.w , self.xw)

            self.EEE = (self.sigma**2) *\
                 (\
                     self.Uw - np.trace(\
                         np.linalg.solve(self.A, self.Pw) )\
                     +   np.trace(self.W.dot(\
                         self.Qw - self.Sw.dot(np.linalg.solve(self.A, self.H)) -\
                         self.H.T.dot(np.linalg.solve(self.A, self.Sw.T)) +\
                         self.H.T.dot(np.linalg.solve(self.A, self.Pw))\
                         .dot(np.linalg.solve(self.A, self.H))\
                                            )\
                                 )\
                 )\
                 + (self.e.T).dot(self.Pw).dot(self.e)\
                 + 2.0*(self.beta.T).dot(self.Sw).dot(self.e)\
                 + (self.beta.T).dot(self.Qw).dot(self.beta)

            self.EE2 = (self.sigma**2) *\
                 (\
                     self.U - self.T.dot(np.linalg.solve(self.A, self.T.T)) +\
                     ( (self.R - self.T.dot(np.linalg.solve(self.A,self.H)) ) )\
                     .dot( self.W )\
                     .dot( (self.R - self.T.dot(np.linalg.solve(self.A,self.H)).T ))\
                 )\
                 + ( self.R.dot(self.beta) + self.T.dot(self.e) )**2

            self.EV = self.EEE - self.EE2
            print("xw:",self.xw,"E(V_",self.w,"):",self.EV)
            self.senseindex[P] = self.EV


    def totaleffectvariance(self):
        print("\n*** Calculate total effect variance ***")
        self.senseindexwb = np.zeros([self.m.size])
        self.EVTw = np.zeros([self.m.size])

        #### this is another constant
        #### it's value is tiny since I divided by sigma... maybe sigma problem...
        self.EVf = (self.sigma**2) *\
            (\
                 self.U - self.T.dot( np.linalg.solve(self.A/(self.sigma**2), self.T.T) ) +\
                 ((self.R - self.T.dot( np.linalg.solve(self.A/(self.sigma**2),self.H) ))\
                 .dot(self.W)\
                 .dot((self.R - self.T.dot(np.linalg.solve(self.A/(self.sigma**2), self.H))).T )\
                 )\
            )
        
        print("EVf:", self.EVf)


        for P in range(0,len(self.m)):
            self.w = [P]
            self.wb = []
            for k in range(0,len(self.m)):
                if k not in self.w:
                    self.wb.append(k)

            ## swap around so we calc E*[V_wb]
            temp = self.w
            self.w = self.wb
            self.wb = temp
            ## then define xw as the means (value doesn't matter for sensitivity)
            self.xw = self.m[self.w]

            #### calculate E*[V_wb]
            print(self.w , self.xw)
            self.UPSQRT(self.w , self.xw)

            self.EEE = (self.sigma**2) *\
                 (\
                     self.Uw - np.trace(\
                         np.linalg.solve(self.A, self.Pw) )\
                     +   np.trace(self.W.dot(\
                         self.Qw - self.Sw.dot(np.linalg.solve(self.A, self.H)) -\
                         self.H.T.dot(np.linalg.solve(self.A, self.Sw.T)) +\
                         self.H.T.dot(np.linalg.solve(self.A, self.Pw))\
                         .dot(np.linalg.solve(self.A, self.H))\
                                            )\
                                 )\
                 )\
                 + (self.e.T).dot(self.Pw).dot(self.e)\
                 + 2.0*(self.beta.T).dot(self.Sw).dot(self.e)\
                 + (self.beta.T).dot(self.Qw).dot(self.beta)

            self.EE2 = (self.sigma**2) *\
                 (\
                     self.U - self.T.dot(np.linalg.solve(self.A, self.T.T)) +\
                     ( (self.R - self.T.dot(np.linalg.solve(self.A,self.H)) ) )\
                     .dot( self.W )\
                     .dot( (self.R - self.T.dot(np.linalg.solve(self.A,self.H)).T ))\
                 )\
                 + ( self.R.dot(self.beta) + self.T.dot(self.e) )**2

            self.EV = self.EEE - self.EE2
            print("xw:",self.xw,"E(V_",self.w,"):",self.EV)
            self.senseindexwb[P] = self.EV

            #########################

            print("senseindexwb" , self.w , ":" , self.senseindexwb[P] )

            self.EVTw[P] = self.EVf - self.senseindexwb[P]
            print("EVT" , P , ":" , self.EVTw[P])


    def UPSQRT_const(self):

        ############# T #############
        self.T  = np.zeros([self.x[:,0].size])
        self.T1 = np.sqrt( self.B.dot(np.linalg.inv(self.B + 2.0*self.C)) ) 
        self.T2 = 0.5*2.0*self.C.dot(self.B).dot( np.linalg.inv(self.B + 2.0*self.C) )
        self.T3 = (self.x - self.m)**2
 
        for k in range(0, self.x[:,0].size):
            self.T[k]= np.prod( (self.T1.dot(np.exp(-self.T2.dot(self.T3[k])))) )

        ############# RQSPU #############
        self.R = np.append([1.0], self.m)
        self.Q = np.outer(self.R.T, self.R)
        self.S = np.outer(self.R.T, self.T)
        self.P = np.outer(self.T.T, self.T)
        self.U = np.prod(np.diag(\
                np.sqrt( self.B.dot(np.linalg.inv(self.B+4.0*self.C)) ) ))

        ##### other constant matrices used for RwQw etc.
        self.S1 = np.sqrt( self.B.dot( np.linalg.inv(self.B + 2.0*self.C) ) ) 
        self.S2 = 0.5*(2.0*self.C*self.B).dot( np.linalg.inv(self.B + 2.0*self.C) )
        self.S3 = (self.x - self.m)**2
        
        self.P1 = self.B.dot( np.linalg.inv(self.B + 2.0*self.C) )
        self.P2 = 0.5*2.0*self.C.dot(self.B).dot( np.linalg.inv(self.B + 2.0*self.C) )
        self.P3 = (self.x - self.m)**2
        self.P4 = np.sqrt( self.B.dot( np.linalg.inv(self.B + 4.0*self.C) ) )
        self.P5 = 0.5*np.linalg.inv(self.B + 4.0*self.C)


    ### create UPSQRT for particular w and xw
    def UPSQRT(self, w, xw):

        ############# Tw #############
 
        Cww = np.diag(np.diag(self.C)[self.w])
        for k in range(0, self.x[:,0].size):
            val  = np.prod( (self.T1.dot(np.exp(-self.T2.dot(self.T3[k]))))[self.wb] )
            self.Tw[k] = val\
              *np.exp(-0.5*(xw-self.x[k][self.w]).T.dot(2.0*Cww).dot(xw-self.x[k][self.w]))

        ############# Rw #############
        Rwno1 = np.array(self.m)
        Rwno1[self.w] = xw
        self.Rw = np.append([1.0], Rwno1)


        ############# Qw #############
        # fill in 1
        self.Qw[0][0] = 1.0
        # fill first row and column
        for i in self.wb + self.w:
            self.Qw[0][1+i] = self.m[i]
            self.Qw[1+i][0] = self.m[i]
        
        mwb_mwb = np.outer( self.m[self.wb], self.m[self.wb].T )
        #print( "m(wb)m(wb)^T :", mwb_mwb )
        for i in range(0,len(self.wb)):
            for j in range(0,len(self.wb)):
                self.Qw[1+self.wb[i]][1+self.wb[j]] = mwb_mwb[i][j]
        
        mwb_mw = np.outer( self.m[self.wb], self.m[self.w].T )
        #print( "m(wb)m(w)^T :", mwb_mw )
        for i in range(0,len(self.wb)):
            for j in range(0,len(self.w)):
                self.Qw[1+self.wb[i]][1+self.w[j]] = mwb_mw[i][j]

        mw_mwb = np.outer( self.m[self.w], self.m[self.wb].T )
        #print( "m(w)m(wb)^T :", mw_mwb )
        for i in range(0,len(self.w)):
            for j in range(0,len(self.wb)):
                self.Qw[1+self.w[i]][1+self.wb[j]] = mw_mwb[i][j]

        mw_mw = np.outer( self.m[self.w] , self.m[self.w].T )
        Bww = np.diag( np.diag(self.B)[self.w] )
        mw_mw_Bww = mw_mw + np.linalg.inv(Bww)
        #print( "m(w)m(w)^T + invBww :", mw_mw_Bww )
        for i in range(0,len(self.w)):
            for j in range(0,len(self.w)):
                self.Qw[1+self.w[i]][1+self.w[j]] = mw_mw_Bww[i][j]
        #print("Qw:\n",self.Qw)


        ############# Sw #############

        for k in range( 0 , 1+len(self.w + self.wb) ):
            for l in range( 0 , self.x[:,0].size ):
                if k == 0:
                    E_star = 1.0
                else:
                    kn=k-1
                    if k-1 in self.wb:
                        E_star = self.m[kn]
                    if k-1 in self.w:
                        E_star=(2*self.C[kn][kn]*self.x[l][kn]\
                               +self.B[kn][kn]*self.m[kn])\
                               /( 2*self.C[kn][kn] + self.B[kn][kn] )
                self.Sw[k,l]=E_star*np.prod( self.S1.dot( np.exp(-self.S2.dot(self.S3[l])) ) )
        #print("Sw:", self.Sw)

        ############# Pw #############

        for k in range( 0 , self.x[:,0].size ):
            for l in range( 0 , self.x[:,0].size ):
                P_prod = np.exp(-self.P2.dot( self.P3[k]+self.P3[l] ))
                self.Pw[k,l]=\
                    np.prod( (self.P1.dot(P_prod))[self.wb] )*\
                    np.prod( (self.P4.dot(\
                        np.exp( -self.P5.dot(\
                        4.0*(self.C*self.C).dot( (self.x[k]-self.x[l])**2 )\
                        +2.0*(self.C*self.B).dot(self.P3[k]+self.P3[l])) ) ))[self.w] )
        #print("P:" , self.P)
        #print("Pw:" , self.Pw)


        ############# Uw #############
        self.Uw = np.prod(np.diag( \
                np.sqrt( self.B.dot(np.linalg.inv(self.B+4.0*self.C)) ))[self.wb])
        #print("U:", self.U, "Uw:", self.Uw)


