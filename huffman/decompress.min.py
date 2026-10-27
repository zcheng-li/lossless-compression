F=len;E=range;A=None
class G:
	def __init__(B,symbol=A):B.symbol=symbol;B.left=A;B.right=A
def K(data):
	B=data
	if not B:return
	F=B[0];A=8
	def C(width):
		nonlocal A;C=0
		for F in E(width):D=B[A//8];C=C<<1|D>>7-A%8&1;A+=1
		return C
	def D():
		if C(1):B=C(F)+1;H=bytes(C(8)for A in E(B));return G(symbol=H)
		A=G();A.left=D();A.right=D();return A
	return D()
def B(source='compressed',destination='out.txt'):
	J='little'
	with open(source,'rb')as G:I=G.read(14);H=int.from_bytes(I[4:12],J);L=int.from_bytes(I[12:14],J);M=G.read(L);N=G.read()
	B=K(M);D=bytearray()
	if B is A:0
	elif B.symbol is not A:O=H//F(B.symbol);D=B.symbol*O
	else:
		C=B
		for P in N:
			for Q in E(7,-1,-1):
				C=C.right if P>>Q&1 else C.left
				if C.symbol is not A:
					D.extend(C.symbol);C=B
					if F(D)==H:break
			if F(D)==H:break
	with open(destination,'wb')as R:R.write(D)
B()