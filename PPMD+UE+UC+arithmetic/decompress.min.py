N=bytes;I=b'';H=len;F=range;import struct as S;L=64;A=1<<L;D=A>>1;E=D>>1;T=A-1;B=5;M=256
class U:
	def __init__(A,max_order=B):A.max_order=max_order;A.history=I;A.contexts={}
	def distributions(A):
		B=set()
		for E in F(H(A.history),-1,-1):
			G=A.history[-E:]if E else I;C=A.contexts.get(G,{});D=[(A,2*C)for(A,C)in sorted(C.items())if A not in B]
			if not D:continue
			D.append((M,H(C)));yield D;B.update(C)
		yield[(A,1)for A in F(256)if A not in B]
	def update(A,symbol):
		B=symbol
		for D in F(H(A.history),-1,-1):
			E=A.history[-D:]if D else I;C=A.contexts.setdefault(E,{})
			if B in C:C[B]+=1;break
			C[B]=1
		if A.max_order:A.history=(A.history+N([B]))[-A.max_order:]
def C(data):
	J=data;V,O=S.unpack_from('<BQ',J,4)
	if O==0:return I
	G=104;W=H(J)*8
	def P():
		nonlocal G
		if G<W:A=J[G//8]>>7-G%8&1
		else:A=0
		G+=1;return A
	A=0;B=T;C=0
	for X in F(L):C=C<<1|P()
	def Y(frequencies):
		J=frequencies;nonlocal A,B,C;G=sum(A for(B,A)in J);H=B-A+1;K=((C-A+1)*G-1)//H;F=0
		for(L,I)in J:
			if K<F+I:break
			F+=I
		B=A+H*(F+I)//G-1;A=A+H*F//G
		while True:
			if B&D==0:0
			elif A&D!=0:A-=D;B-=D;C-=D
			elif A&E!=0 and B&E==0:A-=E;B-=E;C-=E
			else:break
			A<<=1;B=B<<1|1;C=C<<1|P()
		return L
	Q=U(V);R=bytearray()
	for X in F(O):
		for Z in Q.distributions():
			K=Y(Z)
			if K!=M:break
		R.append(K);Q.update(K)
	return N(R)
def G(source='compressed',destination='out.txt'):
	with open(source,'rb')as A:B=C(A.read())
	with open(destination,'wb')as D:D.write(B)
if __name__=='__main__':G()