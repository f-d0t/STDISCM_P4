from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GradeRecord(_message.Message):
    __slots__ = ("enrollment_id", "course_id", "course_code", "course_title", "student_username", "grade", "status")
    ENROLLMENT_ID_FIELD_NUMBER: _ClassVar[int]
    COURSE_ID_FIELD_NUMBER: _ClassVar[int]
    COURSE_CODE_FIELD_NUMBER: _ClassVar[int]
    COURSE_TITLE_FIELD_NUMBER: _ClassVar[int]
    STUDENT_USERNAME_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    enrollment_id: int
    course_id: int
    course_code: str
    course_title: str
    student_username: str
    grade: float
    status: str
    def __init__(self, enrollment_id: _Optional[int] = ..., course_id: _Optional[int] = ..., course_code: _Optional[str] = ..., course_title: _Optional[str] = ..., student_username: _Optional[str] = ..., grade: _Optional[float] = ..., status: _Optional[str] = ...) -> None: ...

class EnrollRequest(_message.Message):
    __slots__ = ("student_username", "course_id")
    STUDENT_USERNAME_FIELD_NUMBER: _ClassVar[int]
    COURSE_ID_FIELD_NUMBER: _ClassVar[int]
    student_username: str
    course_id: int
    def __init__(self, student_username: _Optional[str] = ..., course_id: _Optional[int] = ...) -> None: ...

class EnrollResponse(_message.Message):
    __slots__ = ("success", "message", "enrollment_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ENROLLMENT_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    enrollment_id: int
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., enrollment_id: _Optional[int] = ...) -> None: ...

class ViewGradesRequest(_message.Message):
    __slots__ = ("student_username",)
    STUDENT_USERNAME_FIELD_NUMBER: _ClassVar[int]
    student_username: str
    def __init__(self, student_username: _Optional[str] = ...) -> None: ...

class ViewGradesResponse(_message.Message):
    __slots__ = ("records",)
    RECORDS_FIELD_NUMBER: _ClassVar[int]
    records: _containers.RepeatedCompositeFieldContainer[GradeRecord]
    def __init__(self, records: _Optional[_Iterable[_Union[GradeRecord, _Mapping]]] = ...) -> None: ...

class ListEnrollmentsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListEnrollmentsResponse(_message.Message):
    __slots__ = ("records",)
    RECORDS_FIELD_NUMBER: _ClassVar[int]
    records: _containers.RepeatedCompositeFieldContainer[GradeRecord]
    def __init__(self, records: _Optional[_Iterable[_Union[GradeRecord, _Mapping]]] = ...) -> None: ...

class UploadGradeRequest(_message.Message):
    __slots__ = ("faculty_username", "enrollment_id", "grade")
    FACULTY_USERNAME_FIELD_NUMBER: _ClassVar[int]
    ENROLLMENT_ID_FIELD_NUMBER: _ClassVar[int]
    GRADE_FIELD_NUMBER: _ClassVar[int]
    faculty_username: str
    enrollment_id: int
    grade: float
    def __init__(self, faculty_username: _Optional[str] = ..., enrollment_id: _Optional[int] = ..., grade: _Optional[float] = ...) -> None: ...

class UnenrollRequest(_message.Message):
    __slots__ = ("student_username", "course_id")
    STUDENT_USERNAME_FIELD_NUMBER: _ClassVar[int]
    COURSE_ID_FIELD_NUMBER: _ClassVar[int]
    student_username: str
    course_id: int
    def __init__(self, student_username: _Optional[str] = ..., course_id: _Optional[int] = ...) -> None: ...

class UnenrollResponse(_message.Message):
    __slots__ = ("success", "message", "enrollment_id")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ENROLLMENT_ID_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    enrollment_id: int
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., enrollment_id: _Optional[int] = ...) -> None: ...

class UploadGradeResponse(_message.Message):
    __slots__ = ("success", "message", "updated_grade", "updated_record")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_GRADE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_RECORD_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    updated_grade: float
    updated_record: GradeRecord
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., updated_grade: _Optional[float] = ..., updated_record: _Optional[_Union[GradeRecord, _Mapping]] = ...) -> None: ...
