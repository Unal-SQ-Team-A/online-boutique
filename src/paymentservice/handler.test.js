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

function freezeClock(t, date) {
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
}

function clearComponentCache(t) {
  for (const file of [modulePaths.server, modulePaths.charge]) {
    const resolved = require.resolve(file);
    delete require.cache[resolved];
    t.after(() => {
      delete require.cache[resolved];
    });
  }
}

function mockModules(t, stubs) {
  const originalLoad = Module._load;
  Module._load = function (request, parent, isMain) {
    if (Object.hasOwn(stubs, request)) {
      return stubs[request];
    }
    return originalLoad.call(this, request, parent, isMain);
  };
  clearComponentCache(t);
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

function grpcStubs(capturedServices) {
  class FakeServer {
    addService(definition, implementation) {
      capturedServices.push({ definition, implementation });
    }

    bindAsync() {}

    start() {}
  }

  return {
    '@grpc/grpc-js': {
      Server: FakeServer,
      ServerCredentials: { createInsecure: () => ({}) },
      loadPackageDefinition: () => ({
        hipstershop: { PaymentService: { service: { charge: null } } },
        grpc: { health: { v1: { Health: { service: { check: null } } } } }
      })
    },
    '@grpc/proto-loader': { loadSync: () => ({}) }
  };
}

function chargeStubs(t, { cardDetails, now, validatorCalls, logs }) {
  freezeClock(t, now);
  return {
    'simple-card-validator': (number) => {
      validatorCalls.push(number);
      return { getCardDetails: () => cardDetails };
    },
    uuid: { v4: () => FixedTransactionId },
    pino: () => ({ info: (message) => logs.push(message) })
  };
}

function loadServer(t, { chargeImpl, loggerImpl, capturedServices = [] } = {}) {
  mockModules(t, {
    ...grpcStubs(capturedServices),
    './charge': chargeImpl || (() => ({ transaction_id: FixedTransactionId })),
    './logger': loggerImpl || { info: () => {} }
  });
  return require(modulePaths.server);
}

function loadRealChargeServer(t, { cardDetails, now = FixedNow }) {
  const validatorCalls = [];
  const logs = [];
  mockModules(t, {
    ...grpcStubs([]),
    ...chargeStubs(t, { cardDetails, now, validatorCalls, logs }),
    './logger': { info: () => {} }
  });
  return { Server: require(modulePaths.server), validatorCalls, logs };
}

function loadCharge(t, { cardDetails, now = FixedNow }) {
  const validatorCalls = [];
  const logs = [];
  mockModules(t, chargeStubs(t, { cardDetails, now, validatorCalls, logs }));
  return { charge: require(modulePaths.charge), logs, validatorCalls };
}

function captureWarnings(t) {
  const warnings = [];
  const originalWarn = console.warn;
  console.warn = (...args) => warnings.push(args);
  t.after(() => {
    console.warn = originalWarn;
  });
  return warnings;
}

function captureCallback() {
  const calls = [];
  return {
    calls,
    callback: (...args) => {
      calls.push(args);
    }
  };
}

test('TC-PAY-01 ChargeServiceHandler delega en charge y responde con transaction_id', (t) => {
  const request = makeRequest();
  const logs = [];
  const expectedResponse = { transaction_id: FixedTransactionId };
  let receivedRequest;
  const HipsterShopServer = loadServer(t, {
    chargeImpl: (input) => {
      receivedRequest = input;
      return expectedResponse;
    },
    loggerImpl: { info: (message) => logs.push(message) }
  });
  const { calls, callback } = captureCallback();

  HipsterShopServer.ChargeServiceHandler({ request }, callback);

  assert.deepStrictEqual(receivedRequest, request);
  assert.strictEqual(calls.length, 1);
  assert.deepStrictEqual(calls[0], [null, expectedResponse]);
  assert.deepStrictEqual(logs, [
    `PaymentService#Charge invoked with request ${JSON.stringify(request)}`
  ]);
});

test('TC-PAY-02 ChargeServiceHandler propaga error de dominio sin responder', (t) => {
  const error = new Error('Credit card info is invalid');
  error.code = 400;
  const HipsterShopServer = loadServer(t, {
    chargeImpl: () => {
      throw error;
    }
  });
  const warnings = captureWarnings(t);
  const { calls, callback } = captureCallback();

  HipsterShopServer.ChargeServiceHandler({ request: makeRequest() }, callback);

  assert.strictEqual(calls.length, 1);
  assert.strictEqual(calls[0].length, 1);
  assert.strictEqual(calls[0][0], error);
  assert.deepStrictEqual(warnings, [[error]]);
});

test('TC-PAY-03 ChargeServiceHandler propaga error inesperado sin transformarlo', (t) => {
  const error = new TypeError('cannot read property');
  const HipsterShopServer = loadServer(t, {
    chargeImpl: () => {
      throw error;
    }
  });
  const warnings = captureWarnings(t);
  const { calls, callback } = captureCallback();

  HipsterShopServer.ChargeServiceHandler({ request: {} }, callback);

  assert.strictEqual(calls.length, 1);
  assert.deepStrictEqual(calls[0], [error]);
  assert.deepStrictEqual(warnings, [[error]]);
});

test('TC-PAY-04 el handler queda registrado como PaymentService.charge', (t) => {
  const capturedServices = [];
  const HipsterShopServer = loadServer(t, { capturedServices });
  const { calls, callback } = captureCallback();

  new HipsterShopServer('proto', 50051);

  assert.strictEqual(capturedServices.length, 2);
  assert.strictEqual(typeof capturedServices[0].implementation.charge, 'function');
  assert.strictEqual(typeof capturedServices[1].implementation.check, 'function');

  capturedServices[0].implementation.charge({ request: makeRequest() }, callback);
  capturedServices[1].implementation.check({}, (...args) => {
    calls.push(args);
  });

  assert.deepStrictEqual(calls[0], [null, { transaction_id: FixedTransactionId }]);
  assert.deepStrictEqual(calls[1], [null, { status: 'SERVING' }]);
  assert.strictEqual(HipsterShopServer.ChargeServiceHandler.name, 'ChargeServiceHandler');
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
  assert.match(logs[0], /Transaction processed: visa ending 1111/);
  assert.match(logs[0], /USD12\.500000000/);
});

test('TC-PAY-06 Mastercard válida produce transaction_id', (t) => {
  const { charge, logs } = loadCharge(t, {
    cardDetails: { card_type: 'mastercard', valid: true }
  });

  const result = charge(makeRequest({ number: '5555555555554444' }));

  assert.deepStrictEqual(result, { transaction_id: FixedTransactionId });
  assert.match(logs[0], /Transaction processed: mastercard ending 4444/);
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
  const warnings = captureWarnings(t);
  const { calls, callback } = captureCallback();

  Server.ChargeServiceHandler({ request: { amount: { currency_code: 'USD' } } }, callback);

  assert.strictEqual(calls.length, 1);
  assert.strictEqual(calls[0].length, 1);
  assert.ok(calls[0][0] instanceof TypeError);
  assert.deepStrictEqual(warnings, [[calls[0][0]]]);
});

test('TC-PAY-13 CVV y monto no alteran el transaction_id', (t) => {
  const { charge, logs, validatorCalls } = loadCharge(t, {
    cardDetails: { card_type: 'visa', valid: true }
  });
  const first = makeRequest({ cvv: 111, amount: { currency_code: 'USD', units: 1, nanos: 0 } });
  const second = makeRequest({ cvv: 999, amount: { currency_code: 'EUR', units: 2, nanos: 250000000 } });

  const firstResult = charge(first);
  const secondResult = charge(second);

  assert.deepStrictEqual(firstResult, { transaction_id: FixedTransactionId });
  assert.deepStrictEqual(secondResult, { transaction_id: FixedTransactionId });
  assert.strictEqual(validatorCalls.length, 2);
  assert.strictEqual(logs.length, 2);
  assert.match(logs[0], /USD1\.0/);
  assert.match(logs[1], /EUR2\.250000000/);
});
