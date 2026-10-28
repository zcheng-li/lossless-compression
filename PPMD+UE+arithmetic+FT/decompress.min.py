C=b'';H=len;F=range;K=64;A=1<<K;D=A>>1;E=D>>1;P=A-1;L=256
class Q:
	def __init__(A):A.history=C;A.contexts={}
	def distributions(A):
		B=set()
		for G in F(H(A.history),-1,-1):
			I=A.history[-G:]if G else C;D=A.contexts.get(I,{});E=[(A,200*C)for(A,C)in sorted(D.items())if A not in B]
			if not E:continue
			E.append((L,86*H(D)));yield E;B.update(D)
		yield[(A,1)for A in F(256)if A not in B]
	def update(A,symbol):
		B=symbol
		for E in F(H(A.history),-1,-1):
			G=A.history[-E:]if E else C;D=A.contexts.setdefault(G,{})
			if B in D:D[B]+=1;break
			D[B]=1
		A.history=(A.history+bytes([B]))[-5:]
def B(data):
	I=data;R=int.from_bytes(I[:4],'little');G=32;S=H(I)*8
	def M():
		nonlocal G
		if G<S:A=I[G//8]>>7-G%8&1
		else:A=0
		G+=1;return A
	A=0;B=P;C=0
	for T in F(K):C=C<<1|M()
	def U(frequencies):
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
			A<<=1;B=B<<1|1;C=C<<1|M()
		return L
	N=Q();O=bytearray()
	for T in F(R):
		for V in N.distributions():
			J=U(V)
			if J!=L:break
		O.append(J);N.update(J)
	return O
with open('compressed','rb')as G,open('out.txt','wb')as I:I.write(B(G.read()))