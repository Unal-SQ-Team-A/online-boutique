'use strict';

const assert = require('node:assert/strict');
const Module = require('node:module');
const path = require('node:path');
const { test } = require('node:test');

const RealDate = Date;
const FixedNow = new RealDate(2026, 10, 25, 12, 0, 0);
const YearEndNow = new RealDate(2026, 11, 15, 12, 0, 0);
const FixedTransactionId = '00000000-0000-4000-8000-000000000001';

const modulePaths = {
  server: path.join(__dirname, 'server.js'),
  charge: path.join(__dirname, 'charge.js')
};

function createSpy(t, implementation = () => undefined) {
  const calls = [];
  const spy = (...args) => {
    calls.push(args);
    return implementation(...args);
  };
  return { spy, calls };
}

function createStub(implementation) {
  return implementation;
}

function createStrictMock(t, expectedCalls, implementation = () => undefined) {
  const actualCalls = [];
  t.after(() => assert.deepStrictEqual(actualCalls, expectedCalls));
  return (...args) => {
    actualCalls.push(args);
    return implementation(...args);
  };
}

function createFakeServer(t) {
  return {
    services: [],
    boundAddress: null,
    credentials: null,
    started: false,
    addService(definition, implementation) {
      this.services.push({ definition, implementation });
    },
    bindAsync(address, credentials, callback) {
      this.boundAddress = address;
      this.credentials = credentials;
      if (typeof callback === 'function') {
        callback(null, address);
      }
    },
    start() {
      this.started = true;
    }
  };
}

function createFakeClock(t, date) {
  const timestamp = date.getTime();
  class FakeDate extends RealDate {
    constructor(...args) {
      if (args.length === 0) {
        super(timestamp);
      } else {
        super(...args);
      }
    }

    static now() {
      return timestamp;
    }
  }

  const originalDate = globalThis.Date;
  globalThis.Date = FakeDate;
  t.after(() => {
    globalThis.Date = originalDate;
  });

  return { now: timestamp };
}

function createFakeLogger(t, options = {}) {
  const messages = [];
  const filter = options.filter || (() => true);
  const record = (level, message) => {
    if (filter(message, level)) {
      messages.push([level, message]);
    }
  };

  return {
    logger: {
      info: (message) => record('info', message),
      error: (message) => record('error', message),
      warn: (message) => record('warn', message)
    },
    messages
  };
}

function clearComponentCache(t, files) {
  for (const file of files) {
    const resolved = require.resolve(file);
    delete require.cache[resolved];
    t.after(() => {
      delete require.cache[resolved];
    });
  }
}

function interceptRequire(t, stubs, files = []) {
  const originalLoad = Module._load;
  Module._load = function (request, parent, isMain) {
    if (Object.hasOwn(stubs, request)) {
      return stubs[request];
    }
    return originalLoad.call(this, request, parent, isMain);
  };
  if (files.length > 0) {
    clearComponentCache(t, files);
  }
  t.after(() => {
    Module._load = originalLoad;
  });
}

function makeRequest({
  number = '4111111111111111',
  cvv = 123,
  year = 2027,
  month = 11,
  amount = { currency_code: 'USD', units: 12, nanos: 500000000 }
} = {}) {
  return {
    amount,
    credit_card: {
      credit_card_number: number,
      credit_card_cvv: cvv,
      credit_card_expiration_year: year,
      credit_card_expiration_month: month
    }
  };
}

function loadServer(t, { chargeImpl, logger, fakeServer } = {}) {
  const server = fakeServer || createFakeServer(t);
  const loggerDouble = logger || createFakeLogger(t).logger;
  interceptRequire(t, {
    '@grpc/grpc-js': {
      Server: function Server() {
        return server;
      },
      ServerCredentials: { createInsecure: createStub(() => ({})) },
      loadPackageDefinition: createStub(() => ({
        hipstershop: { PaymentService: { service: { charge: null } } },
        grpc: { health: { v1: { Health: { service: { check: null } } } } }
      }))
    },
    '@grpc/proto-loader': { loadSync: createStub(() => ({})) },
    './charge': chargeImpl || createStub(() => ({ transaction_id: FixedTransactionId })),
    './logger': loggerDouble
  }, [modulePaths.server]);
  return { HipsterShopServer: require(modulePaths.server), fakeServer: server };
}

function loadRealChargeServer(t, { cardDetails, now = FixedNow }) {
  const validatorCalls = [];
  const fakeLogger = createFakeLogger(t);
  const fakeClock = createFakeClock(t, now);
  const validatorSpy = createSpy(t, (number) => {
    validatorCalls.push(number);
    return { getCardDetails: () => cardDetails };
  });
  const fakeServer = createFakeServer(t);
  interceptRequire(t, {
    '@grpc/grpc-js': {
      Server: function Server() {
        return fakeServer;
      },
      ServerCredentials: { createInsecure: createStub(() => ({})) },
      loadPackageDefinition: createStub(() => ({
        hipstershop: { PaymentService: { service: { charge: null } } },
        grpc: { health: { v1: { Health: { service: { check: null } } } } }
      }))
    },
    '@grpc/proto-loader': { loadSync: createStub(() => ({})) },
    'simple-card-validator': validatorSpy.spy,
    uuid: { v4: createStub(() => FixedTransactionId) },
    pino: createStub(() => fakeLogger.logger),
    './logger': { info: () => {} }
  }, [modulePaths.server, modulePaths.charge]);
  return {
    Server: require(modulePaths.server),
    validatorCalls,
    logs: fakeLogger.messages,
    fakeClock,
    validatorSpy
  };
}

function loadCharge(t, { cardDetails, now = FixedNow }) {
  const validatorCalls = [];
  const fakeLogger = createFakeLogger(t);
  const fakeClock = createFakeClock(t, now);
  const validatorSpy = createSpy(t, (number) => {
    validatorCalls.push(number);
    return { getCardDetails: () => cardDetails };
  });
  interceptRequire(t, {
    'simple-card-validator': validatorSpy.spy,
    uuid: { v4: createStub(() => FixedTransactionId) },
    pino: createStub(() => fakeLogger.logger)
  }, [modulePaths.charge]);
  return {
    charge: require(modulePaths.charge),
    logs: fakeLogger.messages,
    validatorCalls,
    validatorSpy,
    fakeClock
  };
}

function createWarningSpy(t) {
  const warningSpy = createSpy(t);
  const originalWarn = console.warn;
  console.warn = warningSpy.spy;
  t.after(() => {
    console.warn = originalWarn;
  });
  return warningSpy;
}

test('TC-PAY-01 ChargeServiceHandler delega en charge y responde con transaction_id', (t) => {
  const request = makeRequest();
  const fakeLogger = createFakeLogger(t);
  const expectedResponse = { transaction_id: FixedTransactionId };
  const chargeMock = createStrictMock(t, [[request]], () => expectedResponse);
  const { HipsterShopServer } = loadServer(t, {
    chargeImpl: chargeMock,
    logger: fakeLogger.logger
  });
  const callbackSpy = createSpy(t);

  HipsterShopServer.ChargeServiceHandler({ request }, callbackSpy.spy);

  assert.strictEqual(callbackSpy.calls.length, 1);
  assert.deepStrictEqual(callbackSpy.calls[0], [null, expectedResponse]);
  assert.deepStrictEqual(fakeLogger.messages, [
    ['info', `PaymentService#Charge invoked with request ${JSON.stringify(request)}`]
  ]);
});

test('TC-PAY-02 ChargeServiceHandler propaga error de dominio sin responder', (t) => {
  const error = new Error('Credit card info is invalid');
  error.code = 400;
  const { HipsterShopServer } = loadServer(t, {
    chargeImpl: () => {
      throw error;
    }
  });
  const warningSpy = createWarningSpy(t);
  const callbackSpy = createSpy(t);

  HipsterShopServer.ChargeServiceHandler({ request: makeRequest() }, callbackSpy.spy);

  assert.strictEqual(callbackSpy.calls.length, 1);
  assert.strictEqual(callbackSpy.calls[0].length, 1);
  assert.strictEqual(callbackSpy.calls[0][0], error);
  assert.deepStrictEqual(warningSpy.calls, [[error]]);
});

test('TC-PAY-03 ChargeServiceHandler propaga error inesperado sin transformarlo', (t) => {
  const error = new TypeError('cannot read property');
  const { HipsterShopServer } = loadServer(t, {
    chargeImpl: () => {
      throw error;
    }
  });
  const warningSpy = createWarningSpy(t);
  const callbackSpy = createSpy(t);

  HipsterShopServer.ChargeServiceHandler({ request: {} }, callbackSpy.spy);

  assert.strictEqual(callbackSpy.calls.length, 1);
  assert.deepStrictEqual(callbackSpy.calls[0], [error]);
  assert.deepStrictEqual(warningSpy.calls, [[error]]);
});

test('TC-PAY-04 el handler queda registrado como PaymentService.charge', (t) => {
  const fakeServer = createFakeServer(t);
  const { HipsterShopServer } = loadServer(t, { fakeServer });
  const callbackSpy = createSpy(t);

  const serverInstance = new HipsterShopServer('proto', 50051);
  serverInstance.listen();

  assert.strictEqual(fakeServer.services.length, 2);
  assert.strictEqual(typeof fakeServer.services[0].implementation.charge, 'function');
  assert.strictEqual(typeof fakeServer.services[1].implementation.check, 'function');

  fakeServer.services[0].implementation.charge({ request: makeRequest() }, callbackSpy.spy);
  fakeServer.services[1].implementation.check({}, (...args) => {
    callbackSpy.calls.push(args);
  });

  assert.deepStrictEqual(callbackSpy.calls[0], [null, { transaction_id: FixedTransactionId }]);
  assert.deepStrictEqual(callbackSpy.calls[1], [null, { status: 'SERVING' }]);
  assert.strictEqual(HipsterShopServer.ChargeServiceHandler.name, 'ChargeServiceHandler');
  assert.strictEqual(fakeServer.started, true);
  assert.strictEqual(fakeServer.boundAddress, '[::]:50051');
});

test('TC-PAY-05 Visa válida produce transaction_id y registra últimos 4 dígitos', (t) => {
  const { charge, logs, validatorCalls } = loadCharge(t, {
    cardDetails: { card_type: 'visa', valid: true }
  });
  const request = makeRequest({ number: '4111111111111111' });

  const result = charge(request);

  assert.deepStrictEqual(result, { transaction_id: FixedTransactionId });
  assert.deepStrictEqual(validatorCalls, ['4111111111111111']);
  assert.deepStrictEqual(request, makeRequest({ number: '4111111111111111' }));
  assert.strictEqual(logs.length, 1);
  assert.match(logs[0][1], /Transaction processed: visa ending 1111/);
  assert.match(logs[0][1], /USD12\.500000000/);
});

test('TC-PAY-06 Mastercard válida produce transaction_id', (t) => {
  const { charge, logs } = loadCharge(t, {
    cardDetails: { card_type: 'mastercard', valid: true }
  });

  const result = charge(makeRequest({ number: '5555555555554444' }));

  assert.deepStrictEqual(result, { transaction_id: FixedTransactionId });
  assert.strictEqual(logs.length, 1);
  assert.match(logs[0][1], /Transaction processed: mastercard ending 4444/);
});

test('TC-PAY-07 número inválido lanza InvalidCreditCard con code 400', (t) => {
  const { charge } = loadCharge(t, {
    cardDetails: { card_type: 'visa', valid: false }
  });

  let error;
  try {
    charge(makeRequest());
  } catch (caught) {
    error = caught;
  }

  assert.ok(error instanceof Error);
  assert.strictEqual(error.constructor.name, 'InvalidCreditCard');
  assert.strictEqual(error.message, 'Credit card info is invalid');
  assert.strictEqual(error.code, 400);
});

test('TC-PAY-08 tipo no aceptado lanza UnacceptedCreditCard', (t) => {
  const { charge } = loadCharge(t, {
    cardDetails: { card_type: 'amex', valid: true }
  });

  let error;
  try {
    charge(makeRequest({ number: '378282246310005' }));
  } catch (caught) {
    error = caught;
  }

  assert.ok(error instanceof Error);
  assert.strictEqual(error.constructor.name, 'UnacceptedCreditCard');
  assert.strictEqual(error.message, 'Sorry, we cannot process amex credit cards. Only VISA or MasterCard is accepted.');
  assert.strictEqual(error.code, 400);
});

test('TC-PAY-09 tarjeta vencida lanza ExpiredCreditCard', (t) => {
  const { charge } = loadCharge(t, {
    cardDetails: { card_type: 'visa', valid: true },
    now: FixedNow
  });

  let error;
  try {
    charge(makeRequest({ year: 2026, month: 10 }));
  } catch (caught) {
    error = caught;
  }

  assert.ok(error instanceof Error);
  assert.strictEqual(error.constructor.name, 'ExpiredCreditCard');
  assert.strictEqual(error.message, 'Your credit card (ending 1111) expired on 10/2026');
  assert.strictEqual(error.code, 400);
});

test('TC-PAY-10 vencimiento en el mes actual es aceptado', (t) => {
  const { charge } = loadCharge(t, {
    cardDetails: { card_type: 'visa', valid: true },
    now: FixedNow
  });

  assert.deepStrictEqual(charge(makeRequest({ year: 2026, month: 11 })), {
    transaction_id: FixedTransactionId
  });
});

test('TC-PAY-11 vencimiento en enero del año siguiente es aceptado desde diciembre', (t) => {
  const { charge } = loadCharge(t, {
    cardDetails: { card_type: 'visa', valid: true },
    now: YearEndNow
  });

  assert.deepStrictEqual(charge(makeRequest({ year: 2027, month: 1 })), {
    transaction_id: FixedTransactionId
  });
});

test('TC-PAY-12 request sin credit_card propaga TypeError al callback', (t) => {
  const { Server } = loadRealChargeServer(t, {
    cardDetails: { card_type: 'visa', valid: true }
  });
  const warningSpy = createWarningSpy(t);
  const callbackSpy = createSpy(t);

  Server.ChargeServiceHandler({ request: { amount: { currency_code: 'USD' } } }, callbackSpy.spy);

  assert.strictEqual(callbackSpy.calls.length, 1);
  assert.strictEqual(callbackSpy.calls[0].length, 1);
  assert.ok(callbackSpy.calls[0][0] instanceof TypeError);
  assert.deepStrictEqual(warningSpy.calls, [[callbackSpy.calls[0][0]]]);
});

test('TC-PAY-13 CVV y monto no alteran el transaction_id', (t) => {
  const { charge, logs } = loadCharge(t, {
    cardDetails: { card_type: 'visa', valid: true }
  });
  const first = makeRequest({ cvv: 111, amount: { currency_code: 'USD', units: 1, nanos: 0 } });
  const second = makeRequest({ cvv: 999, amount: { currency_code: 'EUR', units: 2, nanos: 250000000 } });

  const firstResult = charge(first);
  const secondResult = charge(second);

  assert.deepStrictEqual(firstResult, { transaction_id: FixedTransactionId });
  assert.deepStrictEqual(secondResult, { transaction_id: FixedTransactionId });
  assert.strictEqual(logs.length, 2);
  assert.match(logs[0][1], /USD1\.0/);
  assert.match(logs[1][1], /EUR2\.250000000/);
});
