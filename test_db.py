from bot import load_db, save_db
from agent import check, UnknownPayload, RecoverableException
from time import sleep

def check_db():
    db = load_db()
    for chat_id in db.copy().keys():
        user = db.get(chat_id, {})
        cf, ulss = user.get('cf'), user.get('ulss')
        if cf and ulss:
            print('Check', cf, ulss)
            try:
                state, available, unavailable = check(cf, ulss)
            except RecoverableException as e:
                print('HTTP error, will do it later')
            except UnknownPayload as e:
                print(e.html)
                raise e
            else:
                print('  State:', state)
                print('  Available:')
                for l in available:
                    print('    - ' + l)
                print('  Unavailable:')
                for l in unavailable:
                    print('    - ' + l)
            input('Next? ')
            #sleep(1)
            print()
        del db[chat_id]
        save_db(db)

check_db()