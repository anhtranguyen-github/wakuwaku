from datetime import datetime
from typing import Optional, List, Any, Union
from pydantic import BaseModel


# WaniKani ID Type: Supports legacy integers and Supabase UUIDs
WKID = Union[int, str]


class SubjectType(str):
    RADICAL = "radical"
    KANJI = "kanji"
    VOCABULARY = "vocabulary"
    KANA_VOCABULARY = "kana_vocabulary"


class ApiObject(BaseModel):
    id: Optional[WKID] = None
    object: str
    url: str
    data_updated_at: Optional[datetime] = None
    data: dict = {}


class ApiCollection(BaseModel):
    object: str = "collection"
    url: str
    data_updated_at: Optional[datetime] = None
    data: List[dict] = []
    pages: Optional[dict] = None
    total_count: Optional[int] = None


class ApiSubscription(BaseModel):
    active: bool
    max_level_granted: int
    type: str
    period_ends_at: Optional[datetime] = None


class ApiUserInner(BaseModel):
    id: str
    level: int
    username: str
    started_at: Optional[datetime] = None
    profile_url: str
    subscription: ApiSubscription


class ApiUser(BaseModel):
    id: Optional[WKID] = None
    object: str = "user"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiUserInner


class ApiAssignmentInner(BaseModel):
    available_at: Optional[datetime] = None
    burned_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    hidden: bool = False
    passed_at: Optional[datetime] = None
    resurrected_at: Optional[datetime] = None
    srs_stage: int = 0
    started_at: Optional[datetime] = None
    subject_id: WKID
    subject_type: Optional[str] = None
    unlocked_at: Optional[datetime] = None


class ApiAssignment(BaseModel):
    id: Optional[WKID] = None
    object: str = "assignment"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiAssignmentInner


class ApiAssignmentCollection(BaseModel):
    object: str = "collection"
    url: str
    data_updated_at: Optional[datetime] = None
    data: List[dict] = []
    pages: Optional[dict] = None
    total_count: Optional[int] = None


class ApiReviewInner(BaseModel):
    created_at: Optional[datetime] = None
    assignment_id: WKID
    spaced_repetition_system_id: WKID = 1
    subject_id: WKID = 0
    starting_srs_stage: int = 0
    ending_srs_stage: int = 0
    incorrect_meaning_answers: int = 0
    incorrect_reading_answers: int = 0


class ApiReview(BaseModel):
    id: Optional[WKID] = None
    object: str = "review"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiReviewInner


class ApiReviewCollection(BaseModel):
    object: str = "collection"
    url: str
    data_updated_at: Optional[datetime] = None
    data: List[dict] = []
    pages: Optional[dict] = None
    total_count: Optional[int] = None


class ApiReviewStatisticInner(BaseModel):
    created_at: Optional[datetime] = None
    hidden: bool = False
    meaning_correct: int = 0
    meaning_current_streak: int = 0
    meaning_incorrect: int = 0
    meaning_max_streak: int = 0
    reading_correct: int = 0
    reading_current_streak: int = 0
    reading_incorrect: int = 0
    reading_max_streak: int = 0
    percentage_correct: float = 0.0
    subject_id: WKID = 0
    subject_type: str = "vocabulary"


class ApiReviewStatistic(BaseModel):
    id: Optional[WKID] = None
    object: str = "review_statistic"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiReviewStatisticInner


class SyncPreflightRequest(BaseModel):
    api_key: str


class ApiReviewStatisticCollection(BaseModel):
    object: str = "collection"
    url: str
    data_updated_at: Optional[datetime] = None
    data: List[dict] = []
    pages: Optional[dict] = None
    total_count: Optional[int] = None


class ApiStudyMaterialInner(BaseModel):
    created_at: Optional[datetime] = None
    hidden: bool = False
    meaning_note: Optional[str] = None
    meaning_synonyms: List[str] = []
    reading_note: Optional[str] = None
    subject_id: WKID = 0
    subject_type: str = "vocabulary"


class ApiStudyMaterial(BaseModel):
    id: Optional[WKID] = None
    object: str = "study_material"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiStudyMaterialInner


class ApiStudyMaterialCollection(BaseModel):
    object: str = "collection"
    url: str
    data_updated_at: Optional[datetime] = None
    data: List[dict] = []
    pages: Optional[dict] = None
    total_count: Optional[int] = None


class ApiLevelProgressionInner(BaseModel):
    level: int = 1
    created_at: Optional[datetime] = None
    unlocked_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    passed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    abandoned_at: Optional[datetime] = None


class ApiLevelProgression(BaseModel):
    id: Optional[WKID] = None
    object: str = "level_progression"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiLevelProgressionInner


class ApiLevelProgressionCollection(BaseModel):
    object: str = "collection"
    url: str
    data_updated_at: Optional[datetime] = None
    data: List[dict] = []
    pages: Optional[dict] = None
    total_count: Optional[int] = None


class ApiResetInner(BaseModel):
    created_at: Optional[datetime] = None
    original_level: int = 1
    target_level: int = 1
    confirmed_at: Optional[datetime] = None


class ApiReset(BaseModel):
    id: Optional[WKID] = None
    object: str = "reset"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiResetInner


class ApiResetCollection(BaseModel):
    object: str = "collection"
    url: str
    data_updated_at: Optional[datetime] = None
    data: List[dict] = []
    pages: Optional[dict] = None
    total_count: Optional[int] = None


class ApiSubjectMeaning(BaseModel):
    meaning: str
    primary: bool
    accepted_answer: bool


class ApiSubjectAuxiliaryMeaning(BaseModel):
    meaning: str
    type: str


class ApiSubjectBase(BaseModel):
    auxiliary_meanings: List[dict] = []
    characters: Optional[str] = None
    created_at: Optional[datetime] = None
    document_url: Optional[str] = ""
    hidden_at: Optional[datetime] = None
    lesson_position: int = 0
    level: int = 1
    meaning_mnemonic: Optional[str] = ""
    meanings: List[ApiSubjectMeaning] = []
    slug: Optional[str] = ""
    spaced_repetition_system_id: WKID = 1


class ApiCharacterImageBase(BaseModel):
    url: str
    content_type: str


class ApiCharacterImage(BaseModel):
    url: str
    content_type: str
    metadata: dict = {}


class ApiSubjectRadicalInner(BaseModel):
    amalgamation_subject_ids: List[WKID] = []
    character_images: List[dict] = []
    auxiliary_meanings: List[dict] = []
    characters: Optional[str] = None
    created_at: Optional[datetime] = None
    document_url: Optional[str] = ""
    hidden_at: Optional[datetime] = None
    lesson_position: int = 0
    level: int = 1
    meaning_mnemonic: Optional[str] = ""
    meanings: List[ApiSubjectMeaning] = []
    slug: Optional[str] = ""
    spaced_repetition_system_id: WKID = 1


class ApiSubjectRadical(BaseModel):
    id: Optional[WKID] = None
    object: str = "radical"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiSubjectRadicalInner


class ApiSubjectReading(BaseModel):
    reading: str
    primary: bool
    accepted_answer: bool
    type: Optional[str] = None


class ApiSubjectKanjiInner(BaseModel):
    amalgamation_subject_ids: List[WKID] = []
    component_subject_ids: List[WKID] = []
    meaning_hint: Optional[str] = None
    reading_hint: Optional[str] = None
    reading_mnemonic: Optional[str] = ""
    readings: List[ApiSubjectReading] = []
    visually_similar_subject_ids: List[WKID] = []
    auxiliary_meanings: List[dict] = []
    characters: Optional[str] = None
    created_at: Optional[datetime] = None
    document_url: Optional[str] = ""
    hidden_at: Optional[datetime] = None
    lesson_position: int = 0
    level: int = 1
    meaning_mnemonic: Optional[str] = ""
    meanings: List[ApiSubjectMeaning] = []
    slug: Optional[str] = ""
    spaced_repetition_system_id: WKID = 1


class ApiSubjectKanji(BaseModel):
    id: Optional[WKID] = None
    object: str = "kanji"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiSubjectKanjiInner


class ApiSubjectContextSentence(BaseModel):
    en: str
    ja: str


class ApiSubjectPronunciationAudio(BaseModel):
    url: str
    content_type: str
    metadata: dict = {}


class ApiSubjectVocabularyInner(BaseModel):
    component_subject_ids: List[WKID] = []
    context_sentences: List[dict] = []
    meaning_mnemonic: Optional[str] = ""
    parts_of_speech: List[str] = []
    pronunciation_audios: List[dict] = []
    readings: List[ApiSubjectReading] = []
    reading_mnemonic: Optional[str] = ""
    auxiliary_meanings: List[dict] = []
    characters: Optional[str] = None
    created_at: Optional[datetime] = None
    document_url: Optional[str] = ""
    hidden_at: Optional[datetime] = None
    lesson_position: int = 0
    level: int = 1
    meanings: List[ApiSubjectMeaning] = []
    slug: Optional[str] = ""
    spaced_repetition_system_id: WKID = 1


class ApiSubjectVocabulary(BaseModel):
    id: Optional[WKID] = None
    object: str = "vocabulary"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiSubjectVocabularyInner


class ApiSubjectKanaVocabularyInner(BaseModel):
    context_sentences: List[dict] = []
    meaning_mnemonic: Optional[str] = ""
    parts_of_speech: List[str] = []
    pronunciation_audios: List[dict] = []
    auxiliary_meanings: List[dict] = []
    characters: Optional[str] = None
    created_at: Optional[datetime] = None
    document_url: Optional[str] = ""
    hidden_at: Optional[datetime] = None
    lesson_position: int = 0
    level: int = 1
    meanings: List[ApiSubjectMeaning] = []
    slug: Optional[str] = ""
    spaced_repetition_system_id: WKID = 1


class ApiSubjectKanaVocabulary(BaseModel):
    id: Optional[WKID] = None
    object: str = "kana_vocabulary"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiSubjectKanaVocabularyInner


class ApiSubjectCollection(BaseModel):
    object: str = "collection"
    url: str
    data_updated_at: Optional[datetime] = None
    data: List[dict] = []
    pages: Optional[dict] = None
    total_count: Optional[int] = None


class ApiSrsStage(BaseModel):
    interval: Optional[int] = None
    interval_unit: Optional[str] = None
    position: int


class ApiSpacedRepetitionSystemInner(BaseModel):
    created_at: Optional[datetime] = None
    name: str = ""
    description: str = ""
    unlocking_stage_position: int = 0
    starting_stage_position: int = 1
    passing_stage_position: int = 5
    burning_stage_position: int = 9
    stages: List[ApiSrsStage] = []


class ApiSpacedRepetitionSystem(BaseModel):
    id: Optional[WKID] = None
    object: str = "spaced_repetition_system"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiSpacedRepetitionSystemInner


class ApiSpacedRepetitionSystemCollection(BaseModel):
    object: str = "collection"
    url: str
    data_updated_at: Optional[datetime] = None
    data: List[dict] = []
    pages: Optional[dict] = None
    total_count: Optional[int] = None


class ApiSummarySubjects(BaseModel):
    available_at: Optional[datetime] = None
    subject_ids: List[WKID] = []


class ApiSummaryInner(BaseModel):
    lessons: List[dict] = []
    next_reviews_at: Optional[datetime] = None
    reviews: List[dict] = []


class ApiSummary(BaseModel):
    id: Optional[WKID] = None
    object: str = "report"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiSummaryInner


class ApiCreateReviewResponse(BaseModel):
    id: Optional[WKID] = None
    object: str = "review"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiReviewInner
    resources_updated: Optional[dict] = None


class ReviewCreateInner(BaseModel):
    assignment_id: WKID
    incorrect_meaning_answers: int
    incorrect_reading_answers: int
    created_at: Optional[datetime] = None


class ReviewCreate(BaseModel):
    review: ReviewCreateInner


class StudyMaterialCreateInner(BaseModel):
    subject_id: WKID
    meaning_note: Optional[str] = None
    reading_note: Optional[str] = None
    meaning_synonyms: List[str] = []


class StudyMaterialCreate(BaseModel):
    study_material: StudyMaterialCreateInner


class StudyMaterialUpdateInner(BaseModel):
    meaning_note: Optional[str] = None
    reading_note: Optional[str] = None
    meaning_synonyms: List[str] = []


class StudyMaterialUpdate(BaseModel):
    study_material: StudyMaterialUpdateInner


class AssignmentStart(BaseModel):
    started_at: Optional[datetime] = None


class SyncRequest(BaseModel):
    api_key: str
    mode: str = "merge" # merge, overwrite
