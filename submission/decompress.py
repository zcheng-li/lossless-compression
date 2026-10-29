# The submitted Python decoder is automatically minified using
# python-minifier to reduce its source size, which also reduces the
# compiled .pyc size in our implementation. For readability,
# the original, unminified decoder source is shown at the bottom.

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


# STATE_BITS = 64
# FULL_RANGE = 1 << STATE_BITS
# HALF = FULL_RANGE >> 1
# QUARTER = HALF >> 1
# MASK = FULL_RANGE - 1
# ESCAPE = 256

# class PPMModel:
#     def __init__(self):
#         self.history = b""
#         self.contexts = {}

#     def distributions(self):
#         # Start with the longest context, shortening it after each ESCAPE.
#         excluded = set()
#         for order in range(len(self.history), -1, -1):
#             context = self.history[-order:] if order else b""
#             counts_table = self.contexts.get(context, {})
#             frequencies = [(symbol, 200 * count) for symbol, count in sorted(counts_table.items())
#                            if symbol not in excluded]
#             if not frequencies:
#                 continue
#             # Match the encoder's 200 * count weights; ESCAPE gets 86 per
#             # distinct symbol, including those removed by exclusion.
#             frequencies.append((ESCAPE, 86 * len(counts_table)))
#             yield frequencies
#             excluded.update(counts_table)

#         # Order -1: all remaining byte values have equal probability.
#         yield [(symbol, 1) for symbol in range(256) if symbol not in excluded]

#     def update(self, symbol):
#         # Insert into escaped contexts, increment the first predicting one,
#         # then exclude every lower order from this update.
#         for order in range(len(self.history), -1, -1):
#             context = self.history[-order:] if order else b""
#             counts_table = self.contexts.setdefault(context, {})
#             if symbol in counts_table:
#                 counts_table[symbol] += 1
#                 break
#             counts_table[symbol] = 1
#         self.history = (self.history + bytes([symbol]))[-5:]


# def arithmetic_decompress(data):
#     original_size = int.from_bytes(data[:4], "little")

#     bit_position = 4 * 8
#     bit_limit = len(data) * 8

#     def read_bit():
#         nonlocal bit_position
#         if bit_position < bit_limit:
#             bit = (data[bit_position // 8] >> (7 - bit_position % 8)) & 1
#         else:
#             bit = 0
#         bit_position += 1
#         return bit

#     low = 0
#     high = MASK
#     value = 0
#     for _ in range(STATE_BITS):
#         value = (value << 1) | read_bit()

#     def decode_symbol(frequencies):
#         nonlocal low, high, value
#         total = sum(count for _, count in frequencies)
#         width = high - low + 1
#         scaled = ((value - low + 1) * total - 1) // width
#         lower = 0
#         for symbol, count in frequencies:
#             if scaled < lower + count:
#                 break
#             lower += count

#         high = low + width * (lower + count) // total - 1
#         low = low + width * lower // total
#         while True:
#             if (high & HALF) == 0:
#                 pass
#             elif (low & HALF) != 0:
#                 low -= HALF
#                 high -= HALF
#                 value -= HALF
#             elif (low & QUARTER) != 0 and (high & QUARTER) == 0:
#                 low -= QUARTER
#                 high -= QUARTER
#                 value -= QUARTER
#             else:
#                 break
#             low <<= 1
#             high = (high << 1) | 1
#             value = (value << 1) | read_bit()
#         return symbol

#     model = PPMModel()
#     output = bytearray()
#     for _ in range(original_size):
#         for frequencies in model.distributions():
#             symbol = decode_symbol(frequencies)
#             if symbol != ESCAPE:
#                 break
#         output.append(symbol)
#         model.update(symbol)
#     return output


# with open("compressed", "rb") as fin, open("out.txt", "wb") as fout:
#     fout.write(arithmetic_decompress(fin.read()))
