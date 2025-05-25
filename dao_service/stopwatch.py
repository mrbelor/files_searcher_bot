from time import time
from time import sleep

# функция нужна чтобы удобно ставить временные метки
# а также возвращать пройденное время в секундах
def stopWatch(time_point = None, is_return_int = False):
    if time_point:
        raw_res = time() - time_point
        #print(STOPWATCH_MARK, 'фиксация', raw_res) if LOGGING else None
        #res = round(raw_res, 4)
        res = format(raw_res, '.10f') # в секундах с 10 знаками после запятой

        res = float(res) if is_return_int else str(res) + 's'
    
        return res

    else:
        #print(STOPWATCH_MARK, 'временная отметка:', res) if LOGGING else None
        return time()

def stopWatchClosure():
    '''
    при каждом вызове возвращается время прошедшее с прошлого вызова в секундах
    при первом вызове присвоить переменной! sw = stopWatchClosure()
    '''
    time_point = time()
    
    def fun(is_return_int = False):
        nonlocal time_point # обращение на уровень выше
        raw_res = time() - time_point # вычисление сколько прошло
        time_point = time() # обновление временной точки

        res = round(raw_res, 4)
        res = res if is_return_int else str(res) + 's'    
        return res

    return fun


many_num = 100_000_000
def main():

    start_1 = stopWatch()
    res = 0
    numbers = [n for n in range(many_num)]
    for i in numbers:
        res += i
    stop_1 = stopWatch(start_1)
    print(f"Результат первого: {res}")


    start_2 = stopWatch()
    res = 0
    numbers = [n for n in range(many_num)]
    res = sum(numbers)
    stop_2 = stopWatch(start_2)
    print(f"Результат второго: {res}")



    print(f"Время выполнения первого: " + stop_1)
    print(f"Время выполнения второго: " + stop_2)


def main2():
    sw = stopWatchClosure()

    print(sw())
    sleep(3)
    print(sw())
    sleep(4)
    print(sw())
    sleep(1)
    print(sw())

if __name__ == '__main__':
    main()
