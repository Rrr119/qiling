#!/usr/bin/env python3
#
# Cross Platform and Multi Architecture Advanced Binary Emulation Framework
#

from enum import IntEnum


class ADC_SR(IntEnum):
    AWD   = 1 << 0
    EOC   = 1 << 1
    JEOC  = 1 << 2
    JSTRT = 1 << 3
    STRT  = 1 << 4
    OVR   = 1 << 5

class ADC_CR1(IntEnum):
    AWDCH   = 0x1f << 0
    EOCIE   = 1 << 5
    AWDIE   = 1 << 6
    JEOCIE  = 1 << 7
    SCAN    = 1 << 8
    AWDSGL  = 1 << 9
    JAUTO   = 1 << 10
    DISCEN  = 1 << 11
    JDISCEN = 1 << 12
    DISCNUM = 0x7 << 13
    JAWDEN  = 1 << 22
    AWDEN   = 1 << 23
    RES     = 0x3 << 24
    OVRIE   = 1 << 26

class ADC_CR2(IntEnum):
    ADON     = 1 << 0
    CONT     = 1 << 1
    DMA      = 1 << 8
    DDS      = 1 << 9
    EOCS     = 1 << 10
    ALIGN    = 1 << 11
    JEXTSEL  = 0xf << 16
    JEXTEN   = 0x3 << 20
    JSWSTART = 1 << 22
    EXTSEL   = 0xf << 24
    EXTEN    = 0x3 << 28
    SWSTART  = 1 << 30

class ADC_SMPR1(IntEnum):
    SMP10 = 0x7 << 0
    SMP11 = 0x7 << 3
    SMP12 = 0x7 << 6
    SMP13 = 0x7 << 9
    SMP14 = 0x7 << 12
    SMP15 = 0x7 << 15
    SMP16 = 0x7 << 18
    SMP17 = 0x7 << 21
    SMP18 = 0x7 << 24

class ADC_SMPR2(IntEnum):
    SMP0 = 0x7 << 0
    SMP1 = 0x7 << 3
    SMP2 = 0x7 << 6
    SMP3 = 0x7 << 9
    SMP4 = 0x7 << 12
    SMP5 = 0x7 << 15
    SMP6 = 0x7 << 18
    SMP7 = 0x7 << 21
    SMP8 = 0x7 << 24
    SMP9 = 0x7 << 27

class ADC_SQR1(IntEnum):
    SQ13 = 0x1f << 0
    SQ14 = 0x1f << 5
    SQ15 = 0x1f << 10
    SQ16 = 0x1f << 15
    L    = 0xf << 20

class ADC_SQR2(IntEnum):
    SQ7  = 0x1f << 0
    SQ8  = 0x1f << 5
    SQ9  = 0x1f << 10
    SQ10 = 0x1f << 15
    SQ11 = 0x1f << 20
    SQ12 = 0x1f << 25

class ADC_SQR3(IntEnum):
    SQ1 = 0x1f << 0
    SQ2 = 0x1f << 5
    SQ3 = 0x1f << 10
    SQ4 = 0x1f << 15
    SQ5 = 0x1f << 20
    SQ6 = 0x1f << 25

class ADC_JSQR(IntEnum):
    JSQ1 = 0x1f << 0
    JSQ2 = 0x1f << 5
    JSQ3 = 0x1f << 10
    JSQ4 = 0x1f << 15
    JL   = 0x3 << 20

class ADC_DR(IntEnum):
    DATA     = 0xffff << 0
    ADC2DATA = 0xffff << 16
