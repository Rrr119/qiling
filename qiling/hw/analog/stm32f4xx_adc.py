#!/usr/bin/env python3
#
# Cross Platform and Multi Architecture Advanced Binary Emulation Framework
#

import ctypes

from qiling.hw.peripheral import QlPeripheral
from qiling.hw.const.stm32f4xx_adc import ADC_SR, ADC_CR1, ADC_CR2, ADC_DR


class STM32F4xxAdc(QlPeripheral):
    class Type(ctypes.Structure):
        """ the structure available in :
                stm32f401xc
                stm32f401xe
                stm32f405xx
                stm32f407xx
                stm32f410cx
                stm32f410rx
                stm32f410tx
                stm32f411xe
                stm32f412cx
                stm32f412rx
                stm32f412vx
                stm32f412zx
                stm32f413xx
                stm32f415xx
                stm32f417xx
                stm32f423xx
                stm32f427xx
                stm32f429xx
                stm32f437xx
                stm32f439xx
                stm32f446xx
                stm32f469xx
                stm32f479xx
        """

        _fields_ = [
            ("SR"   , ctypes.c_uint32), # ADC status register,                         Address offset: 0x00
            ("CR1"  , ctypes.c_uint32), # ADC control register 1,                      Address offset: 0x04
            ("CR2"  , ctypes.c_uint32), # ADC control register 2,                      Address offset: 0x08
            ("SMPR1", ctypes.c_uint32), # ADC sample time register 1,                  Address offset: 0x0C
            ("SMPR2", ctypes.c_uint32), # ADC sample time register 2,                  Address offset: 0x10
            ("JOFR1", ctypes.c_uint32), # ADC injected channel data offset register 1, Address offset: 0x14
            ("JOFR2", ctypes.c_uint32), # ADC injected channel data offset register 2, Address offset: 0x18
            ("JOFR3", ctypes.c_uint32), # ADC injected channel data offset register 3, Address offset: 0x1C
            ("JOFR4", ctypes.c_uint32), # ADC injected channel data offset register 4, Address offset: 0x20
            ("HTR"  , ctypes.c_uint32), # ADC watchdog higher threshold register,      Address offset: 0x24
            ("LTR"  , ctypes.c_uint32), # ADC watchdog lower threshold register,       Address offset: 0x28
            ("SQR1" , ctypes.c_uint32), # ADC regular sequence register 1,             Address offset: 0x2C
            ("SQR2" , ctypes.c_uint32), # ADC regular sequence register 2,             Address offset: 0x30
            ("SQR3" , ctypes.c_uint32), # ADC regular sequence register 3,             Address offset: 0x34
            ("JSQR" , ctypes.c_uint32), # ADC injected sequence register,              Address offset: 0x38
            ("JDR1" , ctypes.c_uint32), # ADC injected data register 1,                Address offset: 0x3C
            ("JDR2" , ctypes.c_uint32), # ADC injected data register 2,                Address offset: 0x40
            ("JDR3" , ctypes.c_uint32), # ADC injected data register 3,                Address offset: 0x44
            ("JDR4" , ctypes.c_uint32), # ADC injected data register 4,                Address offset: 0x48
            ("DR"   , ctypes.c_uint32), # ADC regular data register,                   Address offset: 0x4C
        ]

    def __init__(self, ql, label, intn=None):
        super().__init__(ql, label)

        self.intn = intn

        ## conversion result source, may be fed by the host before
        ## the firmware starts a conversion
        self.data = 0

    def convert(self):
        """ Complete a regular conversion: load the result into DR, raise EOC
            and pend the ADC interrupt if EOCIE is set.
        """

        self.instance.CR2 &= ~ADC_CR2.SWSTART
        self.instance.DR = self.data & ADC_DR.DATA
        self.instance.SR |= ADC_SR.EOC

        if self.intn is not None and self.instance.CR1 & ADC_CR1.EOCIE:
            self.ql.hw.nvic.set_pending(self.intn)

    @QlPeripheral.monitor()
    def read(self, offset: int, size: int) -> int:
        value = self.raw_read(offset, size)

        ## EOC is cleared by reading DR
        if self.contain(self.struct.DR, offset, size):
            self.instance.SR &= ~ADC_SR.EOC

        return value

    @QlPeripheral.monitor()
    def write(self, offset: int, size: int, value: int):
        self.raw_write(offset, size, value)

        if offset == self.struct.CR2.offset:
            if value & ADC_CR2.SWSTART and self.instance.CR2 & ADC_CR2.ADON:
                self.convert()
