const previousAutostart = process.env.CURRENCY_SERVICE_DISABLE_AUTOSTART;
process.env.CURRENCY_SERVICE_DISABLE_AUTOSTART = '1';

const test = require('node:test');
const assert = require('node:assert/strict');

const { createCurrencyClient } = require('./server.js');

if (previousAutostart === undefined) {
  delete process.env.CURRENCY_SERVICE_DISABLE_AUTOSTART;
} else {
  process.env.CURRENCY_SERVICE_DISABLE_AUTOSTART = previousAutostart;
}

function createMock(expected) {
  return {
    invoke(method, args, callback) {
      const expectation = expected.find(e => e.method === method);

      assert.ok(expectation, `Unexpected call: ${method}`);

      expectation.actual++;

      assert.ok(expectation.actual <= expectation.times);

      expectation.check?.(args);

      callback(...expectation.response);
    },

    verify() {
      for (const expectation of expected) {
        assert.equal(
          expectation.actual,
          expectation.times,
          `Expected ${expectation.times} calls to ${expectation.method}`
        );
      }
    }
  };
}

class CurrencyServiceFake {
  constructor(rates, delayMs = 0) {
    this.rates = rates || require('./data/currency_conversion.json');
    this.delayMs = delayMs;
  }

  _respond(callback, ...args) {
    if (this.delayMs > 0) {
      setTimeout(() => callback(...args), this.delayMs);
    } else {
      callback(...args);
    }
  }

  getSupportedCurrencies(request, callback) {
    this._respond(callback, null, { currency_codes: Object.keys(this.rates) });
  }

  convert(request, callback) {
    const fromCode = request?.from?.currency_code;
    const toCode = request?.to_code;

    if (!Object.hasOwn(this.rates, fromCode) || !Object.hasOwn(this.rates, toCode)) {
      this._respond(callback, new Error('Unsupported currency'), null);
      return;
    }

    const fromRate = Number(this.rates[fromCode]);
    const toRate = Number(this.rates[toCode]);
    const amount = Number(request.from.units) + Number(request.from.nanos) / 1e9;
    const value = (amount / fromRate) * toRate;
    const units = Math.floor(value);
    const nanos = Math.round((value - units) * 1e9);

    this._respond(callback, null, {
      currency_code: toCode,
      units,
      nanos
    });
  }
}

test('TC-CURR-01 Obtener monedas soportadas correctamente.', (t) => {

  const grpcStub = {
    getSupportedCurrencies(request, callback) {
      callback(null, {
        currency_codes: ['EUR', 'USD', 'JPY']
      });
    },
    convert() {}
  };

  const service = createCurrencyClient({
    client: grpcStub,
    logger: { info() {}, error() {} }
  });

  service.getSupportedCurrencies((err, response) => {
    assert.equal(err, null);
    assert.deepEqual(response.currency_codes, ['EUR', 'USD', 'JPY']);
  });
});

test('TC-CURR-02 Convertir CHF a EUR correctamente.', (t) => {

  const grpcStub = {
    getSupportedCurrencies() {},
    convert(request, callback) {
      callback(null, {
        units: 264,
        nanos: 845070423,
        currency_code: 'EUR'
      });
    }
  };

  const service = createCurrencyClient({
    client: grpcStub,
    logger: { info() {}, error() {} }
  });

  const request = {
    from: { currency_code: 'CHF', units: 300, nanos: 0 },
    to_code: 'EUR'
  };

  service.convert(request, (err, response) => {
    assert.equal(err, null);
    assert.equal(response.currency_code, 'EUR');
    assert.equal(response.units, 264);
  });
});

test('TC-CURR-03 Convertir EUR a USD obteniendo valores decimales.', (t) => {

  const grpcStub = {
    getSupportedCurrencies() {},
    convert(request, callback) {
      callback(null, {
        units: 11,
        nanos: 305000000,
        currency_code: 'USD'
      });
    }
  };

  const service = createCurrencyClient({
    client: grpcStub,
    logger: { info() {}, error() {} }
  });

  service.convert({
    from: { currency_code: 'EUR', units: 10, nanos: 0 },
    to_code: 'USD'
  }, (err, response) => {
    assert.equal(err, null);
    assert.equal(response.units, 11);
    assert.equal(response.nanos, 305000000);
    assert.equal(response.currency_code, 'USD');
  });
});

test('TC-CURR-04 Gestionar correctamente un error de conversión.', (t) => {

  const error = new Error('Conversion failed');

  const grpcStub = {
    getSupportedCurrencies() {},
    convert(request, callback) {
      callback(error, null);
    }
  };

  const logger = {
    info() {},
    error() {}
  };

  const service = createCurrencyClient({
    client: grpcStub,
    logger
  });

  service.convert({
    from: { currency_code: 'EUR', units: 10, nanos: 0 },
    to_code: 'JPY'
  }, (err, response) => {
    assert.equal(err, error);
    assert.equal(response, undefined);
  });
});

test('TC-CURR-05 Verificar que se invoque la consulta de monedas soportadas.', (t) => {

  const calls = [];

  const grpcClient = {
    getSupportedCurrencies(request, callback) {
      calls.push(request);
      callback(null, { currency_codes: ['EUR', 'USD', 'JPY'] });
    },
    convert() {}
  };

  const service = createCurrencyClient({
    client: grpcClient,
    logger: { info() {}, error() {} }
  });

  service.getSupportedCurrencies(() => {
    assert.equal(calls.length, 1);
    assert.deepEqual(calls[0], {});
  });
});

test('TC-CURR-06 Verificar los argumentos enviados durante una conversión USD a JPY.', (t) => {

  const calls = [];

  const grpcClient = {
    getSupportedCurrencies() {},
    convert(request, callback) {
      calls.push(request);
      callback(null, {
        units: 11180,
        nanos: 450243255,
        currency_code: 'JPY'
      });
    }
  };

  const service = createCurrencyClient({
    client: grpcClient,
    logger: { info() {}, error() {} }
  });

  service.convert({
    from: { currency_code: 'USD', units: 100, nanos: 0 },
    to_code: 'JPY'
  }, () => {
    assert.equal(calls.length, 1);
    assert.equal(calls[0].from.currency_code, 'USD');
    assert.equal(calls[0].from.units, 100);
    assert.equal(calls[0].to_code, 'JPY');
  });
});

test('TC-CURR-07 Verificar que el formateador reciba la cantidad original y convertida.', (t) => {

  const formattedValues = [];

  const formatter = (money) => {
    formattedValues.push(money);
    return `${money.units} ${money.currency_code}`;
  };

  const grpcClient = {
    getSupportedCurrencies() {},
    convert(request, callback) {
      callback(null, {
        units: 113,
        nanos: 500000000,
        currency_code: 'USD'
      });
    }
  };

  const service = createCurrencyClient({
    client: grpcClient,
    logger: { info() {}, error() {} },
    formatter
  });

  service.convert({
    from: { currency_code: 'EUR', units: 100, nanos: 0 },
    to_code: 'USD'
  }, () => {
    assert.equal(formattedValues.length, 2);
    assert.equal(formattedValues[0].currency_code, 'EUR');
    assert.equal(formattedValues[1].currency_code, 'USD');
  });
});

test('TC-CURR-08 Verificar que se registre un error cuando falle una conversión.', (t) => {

  const loggedErrors = [];

  const grpcClient = {
    getSupportedCurrencies() {},
    convert(request, callback) {
      callback(new Error('Server unavailable'), null);
    }
  };

  const logger = {
    info() {},
    error(message) {
      loggedErrors.push(message);
    }
  };

  const service = createCurrencyClient({
    client: grpcClient,
    logger
  });

  service.convert({
    from: { currency_code: 'EUR', units: 10, nanos: 0 },
    to_code: 'JPY'
  }, () => {
    assert.equal(loggedErrors.length, 1);
    assert.match(loggedErrors[0], /Error in convert/);
  });
});

test('TC-CURR-09 Verificar que se consulte una vez el listado de monedas soportadas.', (t) => {

  const mock = createMock([{
    method: 'getSupportedCurrencies',
    times: 1,
    actual: 0,
    response: [null, { currency_codes: ['EUR', 'USD', 'JPY'] }]
  }]);

  const grpcClient = {
    getSupportedCurrencies(...args) {
      mock.invoke('getSupportedCurrencies', args, args[1]);
    },
    convert() {}
  };

  const service = createCurrencyClient({
    client: grpcClient,
    logger: { info() {}, error() {} }
  });

  service.getSupportedCurrencies(() => {});

  mock.verify();
});

test('TC-CURR-10 Verificar que se solicite una conversión de USD a JPY con los argumentos esperados.', (t) => {

  const mock = createMock([{
    method: 'convert',
    times: 1,
    actual: 0,
    check: args => {
      assert.equal(args[0].from.currency_code, 'USD');
      assert.equal(args[0].from.units, 100);
      assert.equal(args[0].to_code, 'JPY');
    },
    response: [null, {
      units: 11180,
      nanos: 450243255,
      currency_code: 'JPY'
    }]
  }]);

  const grpcClient = {
    getSupportedCurrencies() {},
    convert(...args) {
      mock.invoke('convert', args, args[1]);
    }
  };

  const service = createCurrencyClient({
    client: grpcClient,
    logger: { info() {}, error() {} }
  });

  service.convert({
    from: { currency_code: 'USD', units: 100, nanos: 0 },
    to_code: 'JPY'
  }, () => {});

  mock.verify();
});

test('TC-CURR-11 Verificar que se registre un error cuando falle la conversión.', (t) => {

  const error = new Error('Conversion failed');

  const mock = createMock([{
    method: 'convert',
    times: 1,
    actual: 0,
    response: [error, null]
  }]);

  let loggedErrors = 0;

  const grpcClient = {
    getSupportedCurrencies() {},
    convert(...args) {
      mock.invoke('convert', args, args[1]);
    }
  };

  const logger = {
    info() {},
    error(message) {
      loggedErrors++;
      assert.match(message, /Error in convert/);
    }
  };

  const service = createCurrencyClient({
    client: grpcClient,
    logger
  });

  service.convert({
    from: { currency_code: 'EUR', units: 10, nanos: 0 },
    to_code: 'JPY'
  }, () => {});

  mock.verify();
  assert.equal(loggedErrors, 1);
});

test('TC-CURR-12 Verificar que se registre un error cuando falle la consulta de monedas.', (t) => {

  const error = new Error('Service unavailable');

  const mock = createMock([{
    method: 'getSupportedCurrencies',
    times: 1,
    actual: 0,
    response: [error, null]
  }]);

  let loggedErrors = 0;

  const grpcClient = {
    getSupportedCurrencies(...args) {
      mock.invoke('getSupportedCurrencies', args, args[1]);
    },
    convert() {}
  };

  const logger = {
    info() {},
    error(message) {
      loggedErrors++;
      assert.match(message, /Error in getSupportedCurrencies/);
    }
  };

  const service = createCurrencyClient({
    client: grpcClient,
    logger
  });

  service.getSupportedCurrencies(() => {});

  mock.verify();
  assert.equal(loggedErrors, 1);
});

test('TC-CURR-13 Obtener las monedas soportadas desde el archivo JSON.', (t) => {

  const fake = new CurrencyServiceFake();

  fake.getSupportedCurrencies({}, (err, response) => {
    assert.equal(err, null);
    assert.ok(response.currency_codes.includes('EUR'));
    assert.ok(response.currency_codes.includes('USD'));
    assert.ok(response.currency_codes.includes('JPY'));
  });
});

test('TC-CURR-14 Calcular correctamente una conversión de USD a JPY.', (t) => {

  const fake = new CurrencyServiceFake();

  fake.convert({
    from: { currency_code: 'USD', units: 100, nanos: 0 },
    to_code: 'JPY'
  }, (err, response) => {

    assert.equal(err, null);

    const result = response.units + response.nanos / 1e9;
    const expected = (100 / 1.1305) * 126.40;

    assert.equal(response.currency_code, 'JPY');
    assert.ok(Math.abs(result - expected) <= 0.000000001);
  });
});

test('TC-CURR-15 Calcular conversiones utilizando tasas de cambio modificadas.', (t) => {

  const fake = new CurrencyServiceFake({
    EUR: '1.0',
    USD: '2.0',
    JPY: '100.0'
  });

  fake.convert({
    from: { currency_code: 'EUR', units: 10, nanos: 0 },
    to_code: 'USD'
  }, (err, response) => {

    assert.equal(err, null);
    assert.equal(response.units, 20);
    assert.equal(response.nanos, 0);
    assert.equal(response.currency_code, 'USD');
  });
});

test('TC-CURR-16 Simular un retraso en la respuesta del servicio de monedas.', async (t) => {

  const fake = new CurrencyServiceFake(undefined, 100);

  let callbackExecuted = false;

  const promise = new Promise((resolve, reject) => {
    fake.getSupportedCurrencies({}, (err, response) => {
      callbackExecuted = true;

      if (err) reject(err);
      else resolve(response);
    });
  });

  assert.equal(callbackExecuted, false);

  const response = await promise;

  assert.equal(callbackExecuted, true);
  assert.ok(response.currency_codes.includes('EUR'));
});