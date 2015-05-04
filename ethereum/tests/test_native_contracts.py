from ethereum import tester
from ethereum import utils
from ethereum import native_contracts

"""
test registration

test calling

test creation, how to do it in tester?
"""


class EchoContract(native_contracts.NativeContract):
    address = utils.int_to_addr(2000)

    def _safe_call(self):
        print "echo contract called" * 10
        res, gas, data = 1, self.msg.gas, self.msg.data.data
        return res, gas, data


def test_registry():
    reg = native_contracts.registry
    assert tester.a0 not in reg

    native_contracts.registry.register(EchoContract)
    assert issubclass(native_contracts.registry[EchoContract.address].im_self, EchoContract)
    native_contracts.registry.unregister(EchoContract)


def test_echo_contract():
    native_contracts.registry.register(EchoContract)
    s = tester.state()
    testdata = 'hello'
    r = s._send(tester.k0, EchoContract.address, 0, testdata)
    assert r['output'] == testdata
    native_contracts.registry.unregister(EchoContract)


def test_native_contract_instances():
    native_contracts.registry.register(EchoContract)

    s = tester.state()

    # last 4 bytes of address are used to reference the contract
    data = EchoContract.address[-4:]
    value = 100

    r = s._send(tester.k0, native_contracts.CreateNativeContractInstance.address, value, data)
    eci_address = r['output']
    # expect to get address of new contract instance
    assert len(eci_address) == 20
    # expect that value was transfered to the new contract
    assert s.block.get_balance(eci_address) == value
    assert s.block.get_balance(native_contracts.CreateNativeContractInstance.address) == 0

    # test the new contract
    data = 'hello'
    r = s.send(tester.k0, eci_address, 0, data)
    assert r == data
    native_contracts.registry.unregister(EchoContract)


class SampleNAC(native_contracts.NativeABIContract):
    address = utils.int_to_addr(2001)

    def initialize(ctx, a='int8', c='bool', d='uint8[]'):
        "Constructor (can a constructor return anything?)"

    def afunc(ctx, a='uint16', b='uint16', returns='uint16'):
        return a * b

    def bfunc(ctx, a='uint16', returns='uint16'):
        return ctx.afunc(a, 2)  # direct native call

    def cfunc(ctx, a='uint16', returns=['uint16', 'uint16']):
        return a, a  # returns tuple

    def dfunc(ctx, a='uint16[2]', returns=['uint16']):
        print "dfunc", a
        return a[0] * a[1]

    def add_property(ctx):
        ctx.dummy = True  # must fail


def test_nac_tester():
    assert issubclass(SampleNAC.afunc.im_class, SampleNAC)
    state = tester.state()
    native_contracts.registry.register(SampleNAC)
    sender = tester.k0

    assert 12 == native_contracts.tester_call_method(state, sender, SampleNAC.afunc, 3, 4)
    assert 26 == native_contracts.tester_call_method(state, sender, SampleNAC.bfunc, 13)
    assert 4, 4 == native_contracts.tester_call_method(state, sender, SampleNAC.cfunc, 4)

    # ??? strange error
    #assert 30 == native_contracts.tester_call_method(state, sender, SampleNAC.dfunc, [5, 6])

    # values out of range must fail
    try:
        native_contracts.tester_call_method(state, sender, SampleNAC.bfunc, -1)
    except Exception:
        pass
    else:
        assert False, 'not in range uint16'
    try:
        native_contracts.tester_call_method(state, sender, SampleNAC.afunc, 2**15, 2)
    except Exception:
        pass
    else:
        assert False, 'not in range uint16'
    try:
        native_contracts.tester_call_method(state, sender, SampleNAC.afunc, [1], 2)
    except Exception:
        pass
    else:
        assert False, 'not in range uint16'


def xtest_nac_add_property_fail():
    native_contracts.registry.register(SampleNAC)
    snac = native_contracts.tester_contract(SampleNAC)
    try:
        snac.add_property()
    except TypeError:
        pass
    else:
        assert False, 'properties must not be createable'


class ExtendedSampleNAC(SampleNAC):
    address = utils.int_to_addr(2002)

    storage = dict(owner='address',
                   numbers='unit32[]',
                   tokens='unint32[200]',
                   userids='mapping{address:uint32}'
                   )

    def cfunc(ctx, a='uint16', returns='uint16'):
        a = ctx.block.coinbase
        # raw call
        r = ctx.call(a, 'data')
        # raw call, specifying gaslimit and value
        r = ctx.call(a, 'data', gas=200, value=5)

    def dfunc(ctx, a='uint16'):
        ctx.numbers[200] = 42
        x = ctx.numbers[90]  # return 0 on key error

    def efunc(ctx, a='uint16'):
        # actual msg based call, with automatic en/decoding
        res = ctx.call(SomeContract.afunc, 42, 43)


"""
ToDo:
    Wrap all funcs and make sure, that they are called with the appropriate arguments
"""
