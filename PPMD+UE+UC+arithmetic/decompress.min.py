N=bytes;I=b'';G=len;F=range;import struct as S;L=64;A=1<<L;D=A>>1;E=D>>1;T=A-1;B=5;C=2;M=256
class U:
	def __init__(A,max_order=B,deterministic_scale=C):A.max_order=max_order;A.deterministic_scale=deterministic_scale;A.history=I;A.contexts={}
	def distributions(A):
		C=set()
		for E in F(G(A.history),-1,-1):
			H=A.history[-E:]if E else I;B=A.contexts.get(H,{});J=A.deterministic_scale if G(B)==1 else 1;D=[(A,2*B*J)for(A,B)in sorted(B.items())if A not in C]
			if not D:continue
			D.append((M,G(B)));yield D;C.update(B)
		yield[(A,1)for A in F(256)if A not in C]
	def update(A,symbol):
		B=symbol
		for D in F(G(A.history),-1,-1):
			E=A.history[-D:]if D else I;C=A.contexts.setdefault(E,{})
			if B in C:C[B]+=1;break
			C[B]=1
		if A.max_order:A.history=(A.history+N([B]))[-A.max_order:]
def H(data):
	J=data;V,W,O=S.unpack_from('<BBQ',J,4)
	if O==0:return I
	H=112;X=G(J)*8
	def P():
		nonlocal H
		if H<X:A=J[H//8]>>7-H%8&1
		else:A=0
		H+=1;return A
	A=0;B=T;C=0
	for Y in F(L):C=C<<1|P()
	def Z(frequencies):
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
	Q=U(V,W);R=bytearray()
	for Y in F(O):
		for a in Q.distributions():
			K=Z(a)
			if K!=M:break
		R.append(K);Q.update(K)
	return N(R)
def J(source='compressed',destination='out.txt'):
	with open(source,'rb')as A:B=H(A.read())
	with open(destination,'wb')as C:C.write(B)
if __name__=='__main__':J()