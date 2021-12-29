import time


class Waiter:
    def __init__(self, condition):
        self.condition = condition

    def wait(self, timeout: float) -> bool:
        expires_at = time.time() + timeout
        while time.time() < expires_at:
            if self.condition():
                return True
            time.sleep(0.050)
        return False


class ConditionTrue:
    def __init__(self, f):
        self.f = f

    def __call__(self):
        return self.f()


class ConditionRaises:
    def __init__(self, e):
        self.e = e

    def __call__(self, f) -> bool:
        try:
            f()
        except self.e as e:
            return True
        return False
