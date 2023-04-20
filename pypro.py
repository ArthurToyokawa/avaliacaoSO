import os
import curses
import pycfg
from pyarch import load_binary_into_memory
from pyarch import cpu_t

class pro_t:
	def __init__ (self, state, pc_reg, memory):
		self.state = state
		self.pc_reg = pc_reg
		self.memory = memory
		self.general_regs = [
			[0], [0], [0], [0], [0], [0], [0], [0], 
		]
		#TODO
		# codigo em si do processo
		# arquivos do processo
		# nome do processo
	# vai ler o codigo de um processo e criar
	def block(self):
		self.os.printk('bloqueando processo')
	def exec(self):
		self.os.printk('executando processo')
	def stop(self):
		self.os.printk('parando processo')