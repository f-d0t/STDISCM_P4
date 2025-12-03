from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Course(_message.Message):
    __slots__ = ("id", "code", "title", "slots", "is_open")
    ID_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    IS_OPEN_FIELD_NUMBER: _ClassVar[int]
    id: int
    code: str
    title: str
    slots: int
    is_open: bool
    def __init__(self, id: _Optional[int] = ..., code: _Optional[str] = ..., title: _Optional[str] = ..., slots: _Optional[int] = ..., is_open: bool = ...) -> None: ...

class ListCoursesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListCoursesResponse(_message.Message):
    __slots__ = ("courses",)
    COURSES_FIELD_NUMBER: _ClassVar[int]
    courses: _containers.RepeatedCompositeFieldContainer[Course]
    def __init__(self, courses: _Optional[_Iterable[_Union[Course, _Mapping]]] = ...) -> None: ...

class AddCourseRequest(_message.Message):
    __slots__ = ("code", "title", "slots")
    CODE_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    SLOTS_FIELD_NUMBER: _ClassVar[int]
    code: str
    title: str
    slots: int
    def __init__(self, code: _Optional[str] = ..., title: _Optional[str] = ..., slots: _Optional[int] = ...) -> None: ...

class AddCourseResponse(_message.Message):
    __slots__ = ("course",)
    COURSE_FIELD_NUMBER: _ClassVar[int]
    course: Course
    def __init__(self, course: _Optional[_Union[Course, _Mapping]] = ...) -> None: ...

class CloseCourseRequest(_message.Message):
    __slots__ = ("course_id",)
    COURSE_ID_FIELD_NUMBER: _ClassVar[int]
    course_id: int
    def __init__(self, course_id: _Optional[int] = ...) -> None: ...

class UpdateSlotsRequest(_message.Message):
    __slots__ = ("course_id", "new_slots")
    COURSE_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_SLOTS_FIELD_NUMBER: _ClassVar[int]
    course_id: int
    new_slots: int
    def __init__(self, course_id: _Optional[int] = ..., new_slots: _Optional[int] = ...) -> None: ...

class OperationResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...
