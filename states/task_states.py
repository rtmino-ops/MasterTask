from aiogram.fsm.state import State, StatesGroup


class Registration(StatesGroup):
    choose_role = State()


class CreateTask(StatesGroup):
    title = State()
    description = State()
    category = State()
    budget = State()
    deadline = State()
    location = State()
    confirm = State()


class ExecutorResponse(StatesGroup):
    message = State()
    proposed_price = State()


class DisputeState(StatesGroup):
    reason = State()


class ReviewState(StatesGroup):
    task_id = State()
    rating = State()
    comment = State()