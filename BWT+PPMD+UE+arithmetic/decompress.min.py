H=bytes;N=bytearray;I=b'';E=len;D=range;import struct as S;L=64;A=1<<L;F=A>>1;G=F>>1;T=A-1;B=5;M=256
def U(data,primary_index):
	B=data;G=[0]*256
	for A in B:G[A]+=1
	F=[0]*256;I=0
	for A in D(256):F[A]=I;I+=G[A]
	J=[0]*E(B)
	for(C,A)in enumerate(B):J[C]=F[A];F[A]+=1
	K=N(E(B));C=primary_index
	for L in D(E(B)-1,-1,-1):K[L]=B[C];C=J[C]
	return H(K)
class V:
	def __init__(A,max_order=B):A.max_order=max_order;A.history=I;A.contexts={}
	def distributions(A):
		B=set()
		for G in D(E(A.history),-1,-1):
			H=A.history[-G:]if G else I;C=A.contexts.get(H,{});F=[(A,2*C)for(A,C)in sorted(C.items())if A not in B]
			if not F:continue
			F.append((M,E(C)));yield F;B.update(C)
		yield[(A,1)for A in D(256)if A not in B]
	def update(A,symbol):
		B=symbol
		for F in D(E(A.history),-1,-1):
			G=A.history[-F:]if F else I;C=A.contexts.setdefault(G,{})
			if B in C:C[B]+=1;break
			C[B]=1
		if A.max_order:A.history=(A.history+H([B]))[-A.max_order:]
def C(data):
	J=data;W,O,X=S.unpack_from('<BQQ',J,4)
	if O==0:return I
	H=168;Y=E(J)*8
	def P():
		nonlocal H
		if H<Y:A=J[H//8]>>7-H%8&1
		else:A=0
		H+=1;return A
	A=0;B=T;C=0
	for Z in D(L):C=C<<1|P()
	def a(frequencies):
		J=frequencies;nonlocal A,B,C;E=sum(A for(B,A)in J);H=B-A+1;K=((C-A+1)*E-1)//H;D=0
		for(L,I)in J:
			if K<D+I:break
			D+=I
		B=A+H*(D+I)//E-1;A=A+H*D//E
		while True:
			if B&F==0:0
			elif A&F!=0:A-=F;B-=F;C-=F
			elif A&G!=0 and B&G==0:A-=G;B-=G;C-=G
			else:break
			A<<=1;B=B<<1|1;C=C<<1|P()
		return L
	Q=V(W);R=N()
	for Z in D(O):
		for b in Q.distributions():
			K=a(b)
			if K!=M:break
		R.append(K);Q.update(K)
	return U(R,X)
def J(source='compressed',destination='out.txt'):
	with open(source,'rb')as A:B=C(A.read())
	with open(destination,'wb')as D:D.write(B)
J()