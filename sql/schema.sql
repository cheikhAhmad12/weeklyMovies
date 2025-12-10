-- Unified schema for SensCritique WeeklyMovies
-- Creates vector extension and core tables in one go

CREATE EXTENSION IF NOT EXISTS vector;

-- Drop existing tables in dependency-safe order
DROP TABLE IF EXISTS reviews CASCADE;
DROP TABLE IF EXISTS pays CASCADE;
DROP TABLE IF EXISTS scenaristes CASCADE;
DROP TABLE IF EXISTS realisateurs CASCADE;
DROP TABLE IF EXISTS producteurs CASCADE;
DROP TABLE IF EXISTS genres CASCADE;
DROP TABLE IF EXISTS films CASCADE;

CREATE TABLE films (
    id SERIAL PRIMARY KEY,
    film VARCHAR(255) NOT NULL,
    url TEXT UNIQUE,
    rate FLOAT,
    date_sortie DATE,
    image TEXT,
    bande_originale VARCHAR(255),
    groupe VARCHAR(255),
    annee FLOAT,
    duree FLOAT
);

CREATE TABLE genres (
    id SERIAL PRIMARY KEY,
    film VARCHAR(255),
    genre VARCHAR(255),
    CONSTRAINT genres_unique UNIQUE(film, genre)
);

CREATE TABLE producteurs (
    id SERIAL PRIMARY KEY,
    film VARCHAR(255),
    producteur VARCHAR(255),
    CONSTRAINT producteurs_unique UNIQUE(film, producteur)
);

CREATE TABLE realisateurs (
    id SERIAL PRIMARY KEY,
    film VARCHAR(255),
    realisateur VARCHAR(255),
    CONSTRAINT realisateurs_unique UNIQUE(film, realisateur)
);

CREATE TABLE scenaristes (
    id SERIAL PRIMARY KEY,
    film VARCHAR(255),
    scenariste VARCHAR(255),
    CONSTRAINT scenaristes_unique UNIQUE(film, scenariste)
);

CREATE TABLE pays (
    id SERIAL PRIMARY KEY,
    film VARCHAR(255),
    pays VARCHAR(255),
    CONSTRAINT pays_unique UNIQUE(film, pays)
);

CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    film VARCHAR(255),
    is_negative BOOLEAN,
    title VARCHAR(255),
    likes FLOAT,
    comments FLOAT,
    content TEXT,
    url TEXT UNIQUE,
    embedding VECTOR(384)
);
