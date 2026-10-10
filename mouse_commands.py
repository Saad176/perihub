"""Run mouse writes and their readback away from Qt's UI thread."""
import time
import mouse_direct as mouse


def execute(kind, values, connection):
    with mouse._LOCK:
        if connection is not None:
            info = mouse.find_device()
            if info is None or info['connection'] != connection:
                raise OSError('Mouse connection changed; try the setting again')
        if kind == 'dpi':
            stage, value = values
            mouse.set_dpi_value(stage, value)
            report = mouse._query(0x8c, stage - 1)
            actual = (report[3] + (report[4] << 8) + 1) * 50
        elif kind == 'stage':
            value, = values
            mouse.select_dpi_stage(value)
            actual = mouse._configuration()[1] + 1
        elif kind == 'count':
            value, = values
            mouse.set_stage_count(value)
            actual = mouse._configuration()[0]
        elif kind == 'polling':
            value, = values
            mouse.set_polling_rate(value)
            time.sleep(.75)
            actual = mouse.CODE_POLLING.get(mouse._query(0x8d)[2])
        elif kind == 'debounce_ms':
            value, = values
            mouse.set_debounce(value)
            actual = mouse._query(0x89, 1)[3]
        elif kind == 'dormancy_s':
            value, = values
            mouse.set_dormancy(value)
            report = mouse._query(0x89, 3)
            actual = report[3] + (report[4] << 8)
        else:
            raise ValueError('Unknown mouse command')
        if actual != value:
            raise OSError(f'Mouse did not confirm {value}; read back {actual}')
        return actual
