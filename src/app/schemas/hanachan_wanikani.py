from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class SubjectType(str):
    RADICAL = "radical"
    KANJI = "kanji"
    VOCABULARY = "vocabulary"
    KANA_VOCABULARY = "kana_vocabulary"


class ApiObject(BaseModel):
    id: Optional[int] = None
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
    id: Optional[int] = None
    object: str = "user"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiUserInner


class ApiAssignmentInner(BaseModel):
    available_at: Optional[datetime] = None
    burned_at: Optional[datetime] = None
    created_at: datetime
    hidden: bool
    passed_at: Optional[datetime] = None
    resurrected_at: Optional[datetime] = None
    srs_stage: int
    started_at: Optional[datetime] = None
    subject_id: int
    subject_type: str
    unlocked_at: Optional[datetime] = None


class ApiAssignment(BaseModel):
    id: Optional[int] = None
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
    created_at: datetime
    assignment_id: int
    spaced_repetition_system_id: int
    subject_id: int
    starting_srs_stage: int
    ending_srs_stage: int
    incorrect_meaning_answers: int
    incorrect_reading_answers: int


class ApiReview(BaseModel):
    id: Optional[int] = None
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
    created_at: datetime
    hidden: bool
    meaning_correct: int
    meaning_current_streak: int
    meaning_incorrect: int
    meaning_max_streak: int
    reading_correct: int
    reading_current_streak: int
    reading_incorrect: int
    reading_max_streak: int
    percentage_correct: float
    subject_id: int
    subject_type: str


class ApiReviewStatistic(BaseModel):
    id: Optional[int] = None
    object: str = "review_statistic"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiReviewStatisticInner


class ApiReviewStatisticCollection(BaseModel):
    object: str = "collection"
    url: str
    data_updated_at: Optional[datetime] = None
    data: List[dict] = []
    pages: Optional[dict] = None
    total_count: Optional[int] = None


class ApiStudyMaterialInner(BaseModel):
    created_at: datetime
    hidden: bool
    meaning_note: Optional[str] = None
    meaning_synonyms: List[str] = []
    reading_note: Optional[str] = None
    subject_id: int
    subject_type: str


class ApiStudyMaterial(BaseModel):
    id: Optional[int] = None
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
    level: int
    created_at: datetime
    unlocked_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    passed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    abandoned_at: Optional[datetime] = None


class ApiLevelProgression(BaseModel):
    id: Optional[int] = None
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
    created_at: datetime
    original_level: int
    target_level: int
    confirmed_at: Optional[datetime] = None


class ApiReset(BaseModel):
    id: Optional[int] = None
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
    created_at: datetime
    document_url: str
    hidden_at: Optional[datetime] = None
    lesson_position: int
    level: int
    meaning_mnemonic: str
    meanings: List[ApiSubjectMeaning]
    slug: str
    spaced_repetition_system_id: int


class ApiCharacterImageBase(BaseModel):
    url: str
    content_type: str


class ApiCharacterImage(BaseModel):
    url: str
    content_type: str
    metadata: dict = {}


class ApiSubjectRadicalInner(BaseModel):
    amalgamation_subject_ids: List[int] = []
    character_images: List[dict] = []
    auxiliary_meanings: List[dict] = []
    characters: Optional[str] = None
    created_at: datetime
    document_url: str
    hidden_at: Optional[datetime] = None
    lesson_position: int
    level: int
    meaning_mnemonic: str
    meanings: List[ApiSubjectMeaning]
    slug: str
    spaced_repetition_system_id: int


class ApiSubjectRadical(BaseModel):
    id: Optional[int] = None
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
    amalgamation_subject_ids: List[int] = []
    component_subject_ids: List[int] = []
    meaning_hint: Optional[str] = None
    reading_hint: Optional[str] = None
    reading_mnemonic: str
    readings: List[ApiSubjectReading] = []
    visually_similar_subject_ids: List[int] = []
    auxiliary_meanings: List[dict] = []
    characters: Optional[str] = None
    created_at: datetime
    document_url: str
    hidden_at: Optional[datetime] = None
    lesson_position: int
    level: int
    meaning_mnemonic: str
    meanings: List[ApiSubjectMeaning]
    slug: str
    spaced_repetition_system_id: int


class ApiSubjectKanji(BaseModel):
    id: Optional[int] = None
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
    component_subject_ids: List[int] = []
    context_sentences: List[dict] = []
    meaning_mnemonic: str
    parts_of_speech: List[str] = []
    pronunciation_audios: List[dict] = []
    readings: List[ApiSubjectReading] = []
    reading_mnemonic: str
    auxiliary_meanings: List[dict] = []
    characters: Optional[str] = None
    created_at: datetime
    document_url: str
    hidden_at: Optional[datetime] = None
    lesson_position: int
    level: int
    meanings: List[ApiSubjectMeaning]
    slug: str
    spaced_repetition_system_id: int


class ApiSubjectVocabulary(BaseModel):
    id: Optional[int] = None
    object: str = "vocabulary"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiSubjectVocabularyInner


class ApiSubjectKanaVocabularyInner(BaseModel):
    context_sentences: List[dict] = []
    meaning_mnemonic: str
    parts_of_speech: List[str] = []
    pronunciation_audios: List[dict] = []
    auxiliary_meanings: List[dict] = []
    characters: Optional[str] = None
    created_at: datetime
    document_url: str
    hidden_at: Optional[datetime] = None
    lesson_position: int
    level: int
    meanings: List[ApiSubjectMeaning]
    slug: str
    spaced_repetition_system_id: int


class ApiSubjectKanaVocabulary(BaseModel):
    id: Optional[int] = None
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
    created_at: datetime
    name: str
    description: str
    unlocking_stage_position: int
    starting_stage_position: int
    passing_stage_position: int
    burning_stage_position: int
    stages: List[ApiSrsStage] = []


class ApiSpacedRepetitionSystem(BaseModel):
    id: Optional[int] = None
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
    available_at: datetime
    subject_ids: List[int] = []


class ApiSummaryInner(BaseModel):
    lessons: List[dict] = []
    next_reviews_at: Optional[datetime] = None
    reviews: List[dict] = []


class ApiSummary(BaseModel):
    id: Optional[int] = None
    object: str = "report"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiSummaryInner


class ApiCreateReviewResponse(BaseModel):
    id: Optional[int] = None
    object: str = "review"
    url: str
    data_updated_at: Optional[datetime] = None
    data: ApiReviewInner
    resources_updated: Optional[dict] = None


class ReviewCreateInner(BaseModel):
    assignment_id: int
    incorrect_meaning_answers: int
    incorrect_reading_answers: int
    created_at: Optional[datetime] = None


class ReviewCreate(BaseModel):
    review: ReviewCreateInner


class StudyMaterialCreateInner(BaseModel):
    subject_id: int
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